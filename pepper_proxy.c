#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "ppapi/c/ppp.h"
#include "ppapi/c/ppp_instance.h"
#include "ppapi/c/pp_errors.h"
#include "all_includes.h"

#define PPFP_PATH "/opt/google/chrome/PepperFlash/libpepflashplayer.so"


static int32_t (*orig_PPP_InitializeModule)(PP_Module module, PPB_GetInterface get_browser_interface);
static const void * (*orig_PPP_GetInterface)(const char* interface_name);
static int32_t (*orig_PPP_InitializeBroker)(PP_ConnectInstance_Func* connect_instance_func);
static void (*orig_PPP_ShutdownBroker)(void);
static void *h = NULL;

static PPB_GetInterface orig_get_browser_interface;

static
void
ensure_original_loaded(void)
{
    if (!h) {
        h = dlopen(PPFP_PATH, RTLD_LAZY);
        orig_PPP_InitializeModule = dlsym(h, "PPP_InitializeModule");
        orig_PPP_GetInterface = dlsym(h, "PPP_GetInterface");
        orig_PPP_InitializeBroker = dlsym(h, "PPP_InitializeBroker");
        orig_PPP_ShutdownBroker = dlsym(h, "PPP_ShutdownBroker");
    }
}

#include "trace-wrappers.c"

const void *
PPP_GetInterface(const char *interface_name)
{
    ensure_original_loaded();
    return my_PPP_GetInterface(interface_name);
}

int32_t
PPP_InitializeBroker(PP_ConnectInstance_Func *connect_instance_func)
{
    printf("PPP_InitializeBroker\n");
    if (orig_PPP_InitializeBroker)
        return orig_PPP_InitializeBroker(connect_instance_func);
    else
        return PP_ERROR_FAILED;
}

void
PPP_ShutdownBroker()
{
    printf("PPP_ShutdownBroker\n");
    if (orig_PPP_ShutdownBroker)
        orig_PPP_ShutdownBroker();
}


int32_t
PPP_InitializeModule(PP_Module module, PPB_GetInterface get_browser_interface)
{
    ensure_original_loaded();
    orig_get_browser_interface = get_browser_interface;
    return orig_PPP_InitializeModule(module, my_PPB_GetInterface);
}
