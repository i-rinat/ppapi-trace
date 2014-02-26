from __future__ import print_function
import sys
import glob

from pycparser import c_parser, c_ast, parse_file, c_generator

c_gen = c_generator.CGenerator()
uniq_trace_orig_structs = set()
uniq_trace_structs = set()
uniq_trace_funcs = set()

def gen_trace_functions(ast):
    class MyVisitor(c_ast.NodeVisitor):
        def visit_Struct(self, node):
            if node.name is not None and (node.name.startswith("PPB_") or node.name.startswith("PPP_")) and node.decls is not None:
                if node.name in uniq_trace_funcs:
                    return
                uniq_trace_funcs.add(node.name)
                for a in node.decls:
                    a_func = a.children()[0][1].children()[0][1].children()
                    a_func_args = a_func[0][1]
                    a_func_rettype = a_func[1][1]

                    print("static ", end="")
                    fname = "unknown"
                    if isinstance(a_func_rettype, c_ast.TypeDecl):
                        fname = a_func_rettype.declname
                        a_func_rettype.declname = ""
                        print(c_gen.visit(c_ast.Typedef("dummy", [], [], a_func_rettype)), end="")
                        a_func_rettype.declname = fname
                    elif isinstance(a_func_rettype, c_ast.PtrDecl):
                        a_func_rettype = a_func_rettype.children()[0][1]
                        fname = a_func_rettype.declname
                        a_func_rettype.declname = ""
                        print (c_gen.visit(c_ast.Typedef("dummy", [], [], a_func_rettype)) + " *", end="")
                        a_func_rettype.declname = fname

                    arg_names = (list(c[1].name for c in a_func_args.children() if c[1].name is not None))
                    print(" trace_" + node.name + "_" + fname + "(" + c_gen.visit(a_func_args) + ") {")
                    print("    printf(\"" + node.name + "." + fname + "\\n\");")
                    print("    return orig_" + node.name + "->" + fname + "(" + ", ".join(arg_names) + ");")
                    print("}")

    v = MyVisitor()
    v.visit(ast)

def gen_structs(ast):
    class MyVisitor(c_ast.NodeVisitor):
        def visit_Struct(self, node):
            if node.name is not None and (node.name.startswith("PPB_") or node.name.startswith("PPP_")) and node.decls is not None:
                if node.name in uniq_trace_structs:
                    return
                uniq_trace_structs.add(node.name)
                print("static const struct " + node.name + " trace_" + node.name + " = {")
                for a in node.decls:
                    a_func = a.children()[0][1].children()[0][1].children()
                    a_func_args = a_func[0][1]
                    a_func_rettype = a_func[1][1]

                    fname = "unknown"
                    if isinstance(a_func_rettype, c_ast.TypeDecl):
                        fname = a_func_rettype.declname
                    elif isinstance(a_func_rettype, c_ast.PtrDecl):
                        a_func_rettype = a_func_rettype.children()[0][1]
                        fname = a_func_rettype.declname

                    print("    ." + fname + " = trace_" + node.name + "_" + fname + ",")
                print("};")

    v = MyVisitor()
    v.visit(ast)

def gen_orig_structs(ast):
    class MyVisitor(c_ast.NodeVisitor):
        def visit_Struct(self, node):
            if node.name is not None and (node.name.startswith("PPB_") or node.name.startswith("PPP_")) and node.decls is not None:
                if node.name in uniq_trace_orig_structs:
                    return
                uniq_trace_orig_structs.add(node.name)
                print("static const struct " + node.name + " *orig_" + node.name + ";")

    v = MyVisitor()
    v.visit(ast)

def gen_browser_get_interface(exc):
    print('''static
const void *
my_PPB_GetInterface(const char *interface_name)
{
    printf("get_browser_interface(\\"%s\\")\\n", interface_name);
    const void *orig = orig_get_browser_interface(interface_name);
    if (0) {
''')

    for a in uniq_trace_structs:
        if not a.startswith("PPB_"):
            continue
        if not a in exc:
            print("not found %s" % a, file=sys.stderr)
            def_interface = "42"
        else:
            def_interface = exc[a]
        print('    } else if (strcmp(interface_name, %s) == 0) { // %s' % (def_interface, a))
        print('        orig_%s = orig;' % a)
        print('        return &trace_%s;' % a)

    print("    }")
    print("    printf(\"unknown PPB interface\\n\");");
    print("    return orig;");
    print("}")

def gen_plugin_get_interface(exc):
    print('''static
const void *
my_PPP_GetInterface(const char *interface_name)
{
    printf("get_plugin_interface(\\"%s\\")\\n", interface_name);
    const void *orig = orig_PPP_GetInterface(interface_name);
    if (0) {
''')

    for a in uniq_trace_structs:
        if not a.startswith("PPP_"):
            continue
        if not a in exc:
            print("not found %s" % a, file=sys.stderr)
            def_interface = "42"
        else:
            def_interface = exc[a]
        print('    } else if (strcmp(interface_name, %s) == 0) { // %s' % (def_interface, a))
        print('        orig_%s = orig;' % a)
        print('        return &trace_%s;' % a)

    print("    }")
    print("    printf(\"unknown PPP interface\\n\");");
    print("    return orig;");
    print("}")


for filename in glob.glob('out/*.prep'):
    ast = parse_file(filename, use_cpp=False)
    gen_orig_structs(ast)
    gen_trace_functions(ast)
    gen_structs(ast)

exc = dict()
exc["PPB_OpenGLES2"]="PPB_OPENGLES2_INTERFACE_1_0"
exc["PPB_OpenGLES2InstancedArrays"]="PPB_OPENGLES2_INSTANCEDARRAYS_INTERFACE_1_0"
exc["PPB_OpenGLES2FramebufferBlit"]="PPB_OPENGLES2_FRAMEBUFFERBLIT_INTERFACE_1_0"
exc["PPB_OpenGLES2FramebufferMultisample"]="PPB_OPENGLES2_FRAMEBUFFERMULTISAMPLE_INTERFACE_1_0"
exc["PPB_OpenGLES2ChromiumEnableFeature"]="PPB_OPENGLES2_CHROMIUMENABLEFEATURE_INTERFACE_1_0"
exc["PPB_OpenGLES2ChromiumMapSub"]="PPB_OPENGLES2_CHROMIUMMAPSUB_INTERFACE_1_0"
exc["PPB_OpenGLES2Query"]="PPB_OPENGLES2_QUERY_INTERFACE_1_0"
exc["PPB_VarDictionary_1_0"]="PPB_VAR_DICTIONARY_INTERFACE_1_0"
exc["PPB_Gamepad_1_0"]="PPB_GAMEPAD_INTERFACE_1_0"
exc["PPB_MouseCursor_1_0"]="PPB_MOUSECURSOR_INTERFACE_1_0"
exc["PPB_Core_1_0"]="PPB_CORE_INTERFACE_1_0"
exc["PPB_Graphics2D_1_0"]="PPB_GRAPHICS_2D_INTERFACE_1_0"
exc["PPB_Graphics2D_1_1"]="PPB_GRAPHICS_2D_INTERFACE_1_1"
exc["PPB_NetworkList_1_0"]="PPB_NETWORKLIST_INTERFACE_1_0"
exc["PPB_Ext_Alarms_Dev_0_1"]="PPB_EXT_ALARMS_DEV_INTERFACE_0_1"
exc["PPB_Ext_Socket_Dev_0_1"]="PPB_EXT_SOCKET_DEV_INTERFACE_0_1"
exc["PPB_Ext_Socket_Dev_0_2"]="PPB_EXT_SOCKET_DEV_INTERFACE_0_2"
exc["PPB_Ext_Events_Dev_0_1"]="PPB_EXT_EVENTS_DEV_INTERFACE_0_1"
exc["PPB_URLResponseInfo_1_0"]="PPB_URLRESPONSEINFO_INTERFACE_1_0"
exc["PPB_URLRequestInfo_1_0"]="PPB_URLREQUESTINFO_INTERFACE_1_0"
exc["PPB_Var_1_0"]="PPB_VAR_INTERFACE_1_0"
exc["PPB_Var_1_1"]="PPB_VAR_INTERFACE_1_1"
exc["PPB_HostResolver_1_0"]="PPB_HOSTRESOLVER_INTERFACE_1_0"
exc["PPB_InputEvent_1_0"]="PPB_INPUT_EVENT_INTERFACE_1_0"
exc["PPB_MouseInputEvent_1_0"]="PPB_MOUSE_INPUT_EVENT_INTERFACE_1_0"
exc["PPB_MouseInputEvent_1_1"]="PPB_MOUSE_INPUT_EVENT_INTERFACE_1_1"
exc["PPB_WheelInputEvent_1_0"]="PPB_WHEEL_INPUT_EVENT_INTERFACE_1_0"
exc["PPB_KeyboardInputEvent_1_0"]="PPB_KEYBOARD_INPUT_EVENT_INTERFACE_1_0"
exc["PPB_TouchInputEvent_1_0"]="PPB_TOUCH_INPUT_EVENT_INTERFACE_1_0"
exc["PPB_IMEInputEvent_1_0"]="PPB_IME_INPUT_EVENT_INTERFACE_1_0"
exc["PPB_FileSystem_1_0"]="PPB_FILESYSTEM_INTERFACE_1_0"
exc["PPB_TrueTypeFont_Dev_0_1"]="PPB_TRUETYPEFONT_DEV_INTERFACE_0_1"
exc["PPB_Memory_Dev_0_1"]="PPB_MEMORY_DEV_INTERFACE_0_1"
exc["PPB_Trace_Event_Dev_0_1"]="PPB_TRACE_EVENT_DEV_INTERFACE_0_1"
exc["PPB_Trace_Event_Dev_0_2"]="PPB_TRACE_EVENT_DEV_INTERFACE_0_2"
exc["PPB_GLESChromiumTextureMapping_Dev_0_1"]="PPB_GLES_CHROMIUM_TEXTURE_MAPPING_DEV_INTERFACE_0_1"
exc["PPB_OpenGLES2ChromiumMapSub_Dev_1_0"]="PPB_OPENGLES2_CHROMIUMMAPSUB_DEV_INTERFACE_1_0"
exc["PPB_Widget_Dev_0_3"]="PPB_WIDGET_DEV_INTERFACE_0_3"
exc["PPB_Widget_Dev_0_4"]="PPB_WIDGET_DEV_INTERFACE_0_4"
exc["PPB_DeviceRef_Dev_0_1"]="PPB_DEVICEREF_DEV_INTERFACE_0_1"
exc["PPB_VideoDecoder_Dev_0_16"]="PPB_VIDEODECODER_DEV_INTERFACE_0_16"
exc["PPB_View_Dev_0_1"]="PPB_VIEW_DEV_INTERFACE_0_1"
exc["PPB_Graphics2D_Dev_0_1"]="PPB_GRAPHICS2D_DEV_INTERFACE_0_1"
exc["PPB_FileChooser_Dev_0_5"]="PPB_FILECHOOSER_DEV_INTERFACE_0_5"
exc["PPB_FileChooser_Dev_0_6"]="PPB_FILECHOOSER_DEV_INTERFACE_0_6"
exc["PPB_VideoCapture_Dev_0_2"]="PPB_VIDEOCAPTURE_DEV_INTERFACE_0_2"
exc["PPB_VideoCapture_Dev_0_3"]="PPB_VIDEOCAPTURE_DEV_INTERFACE_0_3"
exc["PPB_Scrollbar_Dev_0_5"]="PPB_SCROLLBAR_DEV_INTERFACE_0_5"
exc["PPB_ResourceArray_Dev_0_1"]="PPB_RESOURCEARRAY_DEV_INTERFACE_0_1"
exc["PPB_Printing_Dev_0_7"]="PPB_PRINTING_DEV_INTERFACE_0_7"
exc["PPB_CursorControl_Dev_0_4"]="PPB_CURSOR_CONTROL_DEV_INTERFACE_0_4"
exc["PPB_URLUtil_Dev_0_6"]="PPB_URLUTIL_DEV_INTERFACE_0_6"
exc["PPB_URLUtil_Dev_0_7"]="PPB_URLUTIL_DEV_INTERFACE_0_7"
exc["PPB_Buffer_Dev_0_4"]="PPB_BUFFER_DEV_INTERFACE_0_4"
exc["PPB_Crypto_Dev_0_1"]="PPB_CRYPTO_DEV_INTERFACE_0_1"
exc["PPB_AudioInput_Dev_0_2"]="PPB_AUDIO_INPUT_DEV_INTERFACE_0_2"
exc["PPB_AudioInput_Dev_0_3"]="PPB_AUDIO_INPUT_DEV_INTERFACE_0_3"
exc["PPB_AudioInput_Dev_0_4"]="PPB_AUDIO_INPUT_DEV_INTERFACE_0_4"
exc["PPB_IMEInputEvent_Dev_0_1"]="PPB_IME_INPUT_EVENT_DEV_INTERFACE_0_1"
exc["PPB_IMEInputEvent_Dev_0_2"]="PPB_IME_INPUT_EVENT_DEV_INTERFACE_0_2"
exc["PPB_Find_Dev_0_3"]="PPB_FIND_DEV_INTERFACE_0_3"
exc["PPB_Var_Deprecated"]="PPB_VAR_DEPRECATED_INTERFACE_0_3"
exc["PPB_Font_Dev_0_6"]="PPB_FONT_DEV_INTERFACE_0_6"
exc["PPB_Testing_Dev_0_7"]="PPB_TESTING_DEV_INTERFACE_0_7"
exc["PPB_Testing_Dev_0_8"]="PPB_TESTING_DEV_INTERFACE_0_8"
exc["PPB_Testing_Dev_0_9"]="PPB_TESTING_DEV_INTERFACE_0_9"
exc["PPB_Testing_Dev_0_91"]="PPB_TESTING_DEV_INTERFACE_0_91"
exc["PPB_Testing_Dev_0_92"]="PPB_TESTING_DEV_INTERFACE_0_92"
exc["PPB_KeyboardInputEvent_Dev_0_2"]="PPB_KEYBOARD_INPUT_EVENT_DEV_INTERFACE_0_2"
exc["PPB_Zoom_Dev_0_2"]="PPB_ZOOM_DEV_INTERFACE_0_2"
exc["PPB_TextInput_Dev_0_1"]="PPB_TEXTINPUT_DEV_INTERFACE_0_1"
exc["PPB_TextInput_Dev_0_2"]="PPB_TEXTINPUT_DEV_INTERFACE_0_2"
exc["PPB_CharSet_Dev_0_4"]="PPB_CHAR_SET_DEV_INTERFACE_0_4"
exc["PPB_AudioConfig_1_0"]="PPB_AUDIO_CONFIG_INTERFACE_1_0"
exc["PPB_AudioConfig_1_1"]="PPB_AUDIO_CONFIG_INTERFACE_1_1"
exc["PPB_Messaging_1_0"]="PPB_MESSAGING_INTERFACE_1_0"
exc["PPB_WebSocket_1_0"]="PPB_WEBSOCKET_INTERFACE_1_0"
exc["PPB_URLLoader_1_0"]="PPB_URLLOADER_INTERFACE_1_0"
exc["PPB_VarArrayBuffer_1_0"]="PPB_VAR_ARRAY_BUFFER_INTERFACE_1_0"
exc["PPB_CharSet_Trusted_1_0"]="PPB_CHARSET_TRUSTED_INTERFACE_1_0"
exc["PPB_URLLoaderTrusted_0_3"]="PPB_URLLOADERTRUSTED_INTERFACE_0_3"
exc["PPB_FileChooserTrusted_0_5"]="PPB_FILECHOOSER_TRUSTED_INTERFACE_0_5"
exc["PPB_FileChooserTrusted_0_6"]="PPB_FILECHOOSER_TRUSTED_INTERFACE_0_6"
exc["PPB_BrowserFont_Trusted_1_0"]="PPB_BROWSERFONT_TRUSTED_INTERFACE_1_0"
exc["PPB_FileIOTrusted_0_4"]="PPB_FILEIOTRUSTED_INTERFACE_0_4"
exc["PPB_BrokerTrusted_0_2"]="PPB_BROKER_TRUSTED_INTERFACE_0_2"
exc["PPB_BrokerTrusted_0_3"]="PPB_BROKER_TRUSTED_INTERFACE_0_3"
exc["PPB_Instance_1_0"]="PPB_INSTANCE_INTERFACE_1_0"
exc["PPB_Audio_1_0"]="PPB_AUDIO_INTERFACE_1_0"
exc["PPB_Audio_1_1"]="PPB_AUDIO_INTERFACE_1_1"
exc["PPB_NetworkProxy_1_0"]="PPB_NETWORKPROXY_INTERFACE_1_0"
exc["PPB_MessageLoop_1_0"]="PPB_MESSAGELOOP_INTERFACE_1_0"
exc["PPB_VarArray_1_0"]="PPB_VAR_ARRAY_INTERFACE_1_0"
exc["PPB_NetAddress_1_0"]="PPB_NETADDRESS_INTERFACE_1_0"
exc["PPB_TCPSocket_1_0"]="PPB_TCPSOCKET_INTERFACE_1_0"
exc["PPB_TCPSocket_1_1"]="PPB_TCPSOCKET_INTERFACE_1_1"
exc["PPB_FileRef_1_0"]="PPB_FILEREF_INTERFACE_1_0"
exc["PPB_FileRef_1_1"]="PPB_FILEREF_INTERFACE_1_1"
exc["PPB_ImageData_1_0"]="PPB_IMAGEDATA_INTERFACE_1_0"
exc["PPB_UDPSocket_1_0"]="PPB_UDPSOCKET_INTERFACE_1_0"
exc["PPB_View_1_0"]="PPB_VIEW_INTERFACE_1_0"
exc["PPB_View_1_1"]="PPB_VIEW_INTERFACE_1_1"
exc["PPB_Flash_Print_1_0"]="PPB_FLASH_PRINT_INTERFACE_1_0"
exc["PPB_NetAddress_Private_0_1"]="PPB_NETADDRESS_PRIVATE_INTERFACE_0_1"
exc["PPB_NetAddress_Private_1_0"]="PPB_NETADDRESS_PRIVATE_INTERFACE_1_0"
exc["PPB_NetAddress_Private_1_1"]="PPB_NETADDRESS_PRIVATE_INTERFACE_1_1"
exc["PPB_TCPSocket_Private_0_3"]="PPB_TCPSOCKET_PRIVATE_INTERFACE_0_3"
exc["PPB_TCPSocket_Private_0_4"]="PPB_TCPSOCKET_PRIVATE_INTERFACE_0_4"
exc["PPB_TCPSocket_Private_0_5"]="PPB_TCPSOCKET_PRIVATE_INTERFACE_0_5"
exc["PPB_FileRefPrivate_0_1"]="PPB_FILEREFPRIVATE_INTERFACE_0_1"
exc["PPB_Flash_File_ModuleLocal_3_0"]="PPB_FLASH_FILE_MODULELOCAL_INTERFACE_3_0"
exc["PPB_Flash_12_4"]="PPB_FLASH_INTERFACE_12_4"
exc["PPB_Flash_12_5"]="PPB_FLASH_INTERFACE_12_5"
exc["PPB_Flash_12_6"]="PPB_FLASH_INTERFACE_12_6"
exc["PPB_Flash_13_0"]="PPB_FLASH_INTERFACE_13_0"
exc["PPB_Flash_MessageLoop_0_1"]="PPB_FLASH_MESSAGELOOP_INTERFACE_0_1"
exc["PPB_TCPServerSocket_Private_0_1"]="PPB_TCPSERVERSOCKET_PRIVATE_INTERFACE_0_1"
exc["PPB_TCPServerSocket_Private_0_2"]="PPB_TCPSERVERSOCKET_PRIVATE_INTERFACE_0_2"
exc["PPB_FlashFullscreen_0_1"]="PPB_FLASHFULLSCREEN_INTERFACE_0_1"
exc["PPB_FlashFullscreen_1_0"]="PPB_FLASHFULLSCREEN_INTERFACE_1_0"
exc["PPB_VideoDestination_Private_0_1"]="PPB_VIDEODESTINATION_PRIVATE_INTERFACE_0_1"
exc["PPB_Flash_Clipboard_4_0"]="PPB_FLASH_CLIPBOARD_INTERFACE_4_0"
exc["PPB_Flash_Clipboard_5_0"]="PPB_FLASH_CLIPBOARD_INTERFACE_5_0"
exc["PPB_Instance_Private_0_1"]="PPB_INSTANCE_PRIVATE_INTERFACE_0_1"
exc["PPB_X509Certificate_Private_0_1"]="PPB_X509CERTIFICATE_PRIVATE_INTERFACE_0_1"
exc["PPB_ContentDecryptor_Private_0_7"]="PPB_CONTENTDECRYPTOR_PRIVATE_INTERFACE_0_7"
exc["PPB_HostResolver_Private_0_1"]="PPB_HOSTRESOLVER_PRIVATE_INTERFACE_0_1"
exc["PPB_PlatformVerification_Private_0_1"]="PPB_PLATFORMVERIFICATION_PRIVATE_INTERFACE_0_1"
exc["PPB_Flash_FontFile_0_1"]="PPB_FLASH_FONTFILE_INTERFACE_0_1"
exc["PPB_OutputProtection_Private_0_1"]="PPB_OUTPUTPROTECTION_PRIVATE_INTERFACE_0_1"
exc["PPB_UDPSocket_Private_0_2"]="PPB_UDPSOCKET_PRIVATE_INTERFACE_0_2"
exc["PPB_UDPSocket_Private_0_3"]="PPB_UDPSOCKET_PRIVATE_INTERFACE_0_3"
exc["PPB_UDPSocket_Private_0_4"]="PPB_UDPSOCKET_PRIVATE_INTERFACE_0_4"
exc["PPB_FileIO_Private_0_1"]="PPB_FILEIO_PRIVATE_INTERFACE_0_1"
exc["PPB_Flash_DeviceID_1_0"]="PPB_FLASH_DEVICEID_INTERFACE_1_0"
exc["PPB_Flash_Menu_0_2"]="PPB_FLASH_MENU_INTERFACE_0_2"
exc["PPB_Talk_Private_1_0"]="PPB_TALK_PRIVATE_INTERFACE_1_0"
exc["PPB_Talk_Private_2_0"]="PPB_TALK_PRIVATE_INTERFACE_2_0"
exc["PPB_Flash_DRM_1_0"]="PPB_FLASH_DRM_INTERFACE_1_0"
exc["PPB_NaCl_Private_1_0"]="PPB_NACL_PRIVATE_INTERFACE_1_0"
exc["PPB_Ext_CrxFileSystem_Private_0_1"]="PPB_EXT_CRXFILESYSTEM_PRIVATE_INTERFACE_0_1"
exc["PPB_VideoSource_Private_0_1"]="PPB_VIDEOSOURCE_PRIVATE_INTERFACE_0_1"
exc["PPB_UMA_Private_0_1"]="PPB_UMA_PRIVATE_INTERFACE_0_1"
exc["PPB_MouseLock_1_0"]="PPB_MOUSELOCK_INTERFACE_1_0"
exc["PPB_Graphics3D_1_0"]="PPB_GRAPHICS_3D_INTERFACE_1_0"
exc["PPB_NetworkMonitor_1_0"]="PPB_NETWORKMONITOR_INTERFACE_1_0"
exc["PPB_FileIO_1_0"]="PPB_FILEIO_INTERFACE_1_0"
exc["PPB_FileIO_1_1"]="PPB_FILEIO_INTERFACE_1_1"
exc["PPB_TextInputController_1_0"]="PPB_TEXTINPUTCONTROLLER_INTERFACE_1_0"
exc["PPB_Fullscreen_1_0"]="PPB_FULLSCREEN_INTERFACE_1_0"
exc["PPB_Console_1_0"]="PPB_CONSOLE_INTERFACE_1_0"

exc["PPB_PDF"] = "PPB_PDF_INTERFACE"
exc["PPB_Proxy_Private"] = "PPB_PROXY_PRIVATE_INTERFACE"
exc["PPB_Flash_File_FileRef"] = "PPB_FLASH_FILE_FILEREF_INTERFACE"

exc["PPP_Flash_BrowserOperations_1_0"]="PPP_FLASH_BROWSEROPERATIONS_INTERFACE_1_0"
exc["PPP_Flash_BrowserOperations_1_2"]="PPP_FLASH_BROWSEROPERATIONS_INTERFACE_1_2"
exc["PPP_Flash_BrowserOperations_1_3"]="PPP_FLASH_BROWSEROPERATIONS_INTERFACE_1_3"
exc["PPP_InputEvent_0_1"]="PPP_INPUT_EVENT_INTERFACE_0_1"
exc["PPP_Instance_Private_0_1"]="PPP_INSTANCE_PRIVATE_INTERFACE_0_1"
exc["PPP_Instance_1_0"]="PPP_INSTANCE_INTERFACE_1_0"
exc["PPP_Instance_1_1"]="PPP_INSTANCE_INTERFACE_1_1"
exc["PPP_MouseLock_1_0"]="PPP_MOUSELOCK_INTERFACE_1_0"
exc["PPP_ContentDecryptor_Private_0_7"]="PPP_CONTENTDECRYPTOR_PRIVATE_INTERFACE_0_7"
exc["PPP_Widget_Dev_0_2"]="PPP_WIDGET_DEV_INTERFACE_0_2"
exc["PPP_Printing_Dev_0_6"]="PPP_PRINTING_DEV_INTERFACE_0_6"
exc["PPP_Scrollbar_Dev_0_2"]="PPP_SCROLLBAR_DEV_INTERFACE_0_2"
exc["PPP_Scrollbar_Dev_0_3"]="PPP_SCROLLBAR_DEV_INTERFACE_0_3"
exc["PPP_VideoCapture_Dev_0_1"]="PPP_VIDEO_CAPTURE_DEV_INTERFACE_0_1"
exc["PPP_VideoDecoder_Dev_0_9"]="PPP_VIDEODECODER_DEV_INTERFACE_0_9"
exc["PPP_VideoDecoder_Dev_0_10"]="PPP_VIDEODECODER_DEV_INTERFACE_0_10"
exc["PPP_VideoDecoder_Dev_0_11"]="PPP_VIDEODECODER_DEV_INTERFACE_0_11"
exc["PPP_Selection_Dev_0_3"]="PPP_SELECTION_DEV_INTERFACE_0_3"
exc["PPP_TextInput_Dev_0_1"]="PPP_TEXTINPUT_DEV_INTERFACE_0_1"
exc["PPP_Zoom_Dev_0_3"]="PPP_ZOOM_DEV_INTERFACE_0_3"
exc["PPP_NetworkState_Dev_0_1"]="PPP_NETWORK_STATE_DEV_INTERFACE_0_1"
exc["PPP_Messaging_1_0"]="PPP_MESSAGING_INTERFACE_1_0"
exc["PPP_Graphics_3D_1_0"]="PPP_GRAPHICS_3D_INTERFACE_1_0"

exc["PPP_Find_Dev"] = "PPP_FIND_DEV_INTERFACE"
exc["PPP_Class_Deprecated"] = '"PPP_Class_Deprecated"'
exc["PPP_Graphics3D_1_0"] = "PPP_GRAPHICS_3D_INTERFACE_1_0"

# find . -type f -exec cat '{}' \; | grep ^#define | grep INTERFACE | grep -v INTERFACE\  | awk '{sub(";", "_", $3); sub("\\.", "_", $3); sub("\\(", "_", $3); sub("\\)", "", $3); print "exc[" $3 "]=\"" $2 "\""}'

gen_browser_get_interface(exc)
gen_plugin_get_interface(exc)
