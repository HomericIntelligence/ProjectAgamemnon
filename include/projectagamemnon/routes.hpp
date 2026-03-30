#pragma once

// Forward declarations to avoid pulling in heavy headers here.
namespace httplib { class Server; }

namespace projectagamemnon {

class Store;
class NatsClient;

/// Register all /v1/ route handlers on the given server.
/// Both Store and NatsClient are passed by reference; they must outlive the
/// server (they are owned by main).
void register_routes(httplib::Server& server, Store& store, NatsClient& nats);

}  // namespace projectagamemnon
