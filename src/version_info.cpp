// Stub source for the library target — provides version symbols.
// The actual main() is in server_main.cpp (server executable target).
#include "projectagamemnon/version.hpp"

namespace projectagamemnon {

const char* get_version() { return kVersion.data(); }
const char* get_project_name() { return kProjectName.data(); }

}  // namespace projectagamemnon
