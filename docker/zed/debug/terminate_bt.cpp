// R9 hunt (docs/todo.md): print the stack of an uncaught C++ exception before the process aborts.
// The ZED wrapper dies with `std::runtime_error: can't compare times with different time sources` and the throw site is
// unknown. An uncaught exception reaches std::terminate before the stack unwinds, so a terminate handler still sees the
// throwing frames. Built and LD_PRELOADed by the `zed` compose service (g++ is in the image; < 1 s at container start).
// Zero cost until an exception escapes; behaviour afterwards is unchanged (abort, exit code -6).
#include <cxxabi.h>
#include <execinfo.h>
#include <pthread.h>
#include <unistd.h>

#include <cstdio>
#include <cstdlib>
#include <exception>
#include <typeinfo>

namespace {

void print_backtrace()
{
  void * frames[128];
  const int n = backtrace(frames, 128);
  char ** syms = backtrace_symbols(frames, n);
  for (int i = 0; i < n; ++i) {
    const char * s = syms ? syms[i] : "?";
    // demangle "lib.so(_ZN...+0x12)" -> "lib.so(Foo::bar()+0x12)"
    const char * open = s ? __builtin_strchr(s, '(') : nullptr;
    const char * plus = open ? __builtin_strchr(open, '+') : nullptr;
    if (open && plus && plus > open + 1) {
      char mangled[512];
      const size_t len = static_cast<size_t>(plus - open - 1) < sizeof(mangled) - 1 ?
        static_cast<size_t>(plus - open - 1) : sizeof(mangled) - 1;
      __builtin_memcpy(mangled, open + 1, len);
      mangled[len] = '\0';
      int status = 0;
      char * dem = abi::__cxa_demangle(mangled, nullptr, nullptr, &status);
      if (status == 0 && dem) {
        fprintf(stderr, "[terminate_bt] #%02d %.*s(%s%s\n", i, static_cast<int>(open - s), s, dem, plus);
        free(dem);
        continue;
      }
    }
    fprintf(stderr, "[terminate_bt] #%02d %s\n", i, s);
  }
  free(syms);
}

void handler()
{
  char tname[32] = "?";
  pthread_getname_np(pthread_self(), tname, sizeof(tname));
  fprintf(stderr, "[terminate_bt] uncaught exception in thread '%s'", tname);
  if (std::exception_ptr e = std::current_exception()) {
    try {
      std::rethrow_exception(e);
    } catch (const std::exception & x) {
      fprintf(stderr, " (%s): %s", typeid(x).name(), x.what());
    } catch (...) {
      fprintf(stderr, " (non-std exception)");
    }
  }
  fprintf(stderr, "\n");
  print_backtrace();
  fflush(stderr);
  abort();
}

__attribute__((constructor)) void install() { std::set_terminate(handler); }

}  // namespace
