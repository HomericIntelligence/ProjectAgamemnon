#pragma once

#include "httplib.h"

namespace projectagamemnon {

/// Register all HTTP route handlers onto the server.
/// Routes return stub JSON responses with TODO markers for real implementation.
void register_routes(httplib::Server& server);

}  // namespace projectagamemnon
