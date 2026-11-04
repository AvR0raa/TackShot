#define UNICODE
#define _UNICODE
#include "onnxruntime_c_api.h"
#include <windows.h>
#include <cstdio>
#include <string>

typedef const OrtApiBase* (*OrtGetApiBaseFn)(void);

static const OrtApi* g_api = nullptr;

static void dumpIO(OrtSession* s, bool input) {
    size_t n = 0;
    if (input) g_api->SessionGetInputCount(s, &n); else g_api->SessionGetOutputCount(s, &n);
    OrtAllocator* alloc = nullptr;
    g_api->GetAllocatorWithDefaultOptions(&alloc);
    for (size_t i = 0; i < n; ++i) {
        char* name = nullptr;
        OrtStatus* st = input ? g_api->SessionGetInputName(s, i, alloc, &name)
                              : g_api->SessionGetOutputName(s, i, alloc, &name);
        if (st) { printf("   name err: %s\n", g_api->GetErrorMessage(st)); continue; }
        OrtTypeInfo* ti = nullptr;
        st = input ? g_api->SessionGetInputTypeInfo(s, i, &ti) : g_api->SessionGetOutputTypeInfo(s, i, &ti);
        std::string shape = "?";
        const char* etype = "?";
        if (!st && ti) {
            const OrtTensorTypeAndShapeInfo* tsi = nullptr;
            g_api->CastTypeInfoToTensorInfo(ti, &tsi);
            if (tsi) {
                size_t dims = 0; g_api->GetDimensionsCount(tsi, &dims);
                int64_t d[8] = {0};
                if (dims <= 8) g_api->GetDimensions(tsi, d, dims);
                shape.clear();
                for (size_t k = 0; k < dims; ++k) {
                    shape += (d[k] < 0 ? std::string("?") : std::to_string(d[k]));
                    if (k + 1 < dims) shape += ",";
                }
                ONNXTensorElementDataType t; g_api->GetTensorElementType(tsi, &t);
                switch (t) {
                case ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT: etype = "float32"; break;
                case ONNX_TENSOR_ELEMENT_DATA_TYPE_UINT8: etype = "uint8"; break;
                case ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64: etype = "int64"; break;
                case ONNX_TENSOR_ELEMENT_DATA_TYPE_INT32: etype = "int32"; break;
                case ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT16: etype = "float16"; break;
                default: etype = "other"; break;
                }
            }
            g_api->ReleaseTypeInfo(ti);
        }
        printf("   %s[%zu] %-24s shape=[%s] type=%s\n", input ? "in " : "out", i, name, shape.c_str(), etype);
        g_api->AllocatorFree(alloc, name);
    }
}

int wmain(int argc, wchar_t** argv) {
    setvbuf(stdout, nullptr, _IONBF, 0);
    printf("[probe] start argc=%d\n", argc);
    if (argc < 2) { printf("usage: ort_probe model.onnx\n"); return 2; }
    HMODULE h = LoadLibraryW(L"onnxruntime.dll");
    if (!h) { printf("load dll failed %lu\n", GetLastError()); return 3; }
    auto fn = (OrtGetApiBaseFn)GetProcAddress(h, "OrtGetApiBase");
    if (!fn) { printf("no OrtGetApiBase\n"); return 4; }
    const OrtApiBase* base = fn();
    printf("ORT %s\n", base->GetVersionString());
    g_api = base->GetApi(ORT_API_VERSION);
    if (!g_api) { printf("api version mismatch\n"); return 5; }

    OrtEnv* env = nullptr;
    g_api->CreateEnv(ORT_LOGGING_LEVEL_ERROR, "probe", &env);
    OrtSessionOptions* opts = nullptr;
    g_api->CreateSessionOptions(&opts);
    g_api->SetIntraOpNumThreads(opts, 2);

    OrtSession* s = nullptr;
    OrtStatus* st = g_api->CreateSession(env, argv[1], opts, &s);
    if (st) { printf("LOAD FAILED: %s\n", g_api->GetErrorMessage(st)); return 1; }
    printf("loaded ok\n");
    dumpIO(s, true);
    dumpIO(s, false);
    return 0;
}
