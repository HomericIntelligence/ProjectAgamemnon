#pragma once

#include <functional>
#include <string>

#include "nlohmann/json.hpp"

namespace projectagamemnon {

/// Thin wrapper around the nats.c client library with JetStream support.
///
/// Designed for graceful degradation: if the NATS server is unavailable,
/// connect() returns false and is_connected() returns false.  All publish /
/// subscribe calls are no-ops when not connected.
class NatsClient {
 public:
  explicit NatsClient(const std::string& url);
  ~NatsClient();

  // Non-copyable, non-movable (holds raw pointers).
  NatsClient(const NatsClient&) = delete;
  NatsClient& operator=(const NatsClient&) = delete;

  /// Connect to the NATS server.  Returns false and logs a warning on failure.
  bool connect();

  /// Close the connection gracefully.
  void close();

  bool is_connected() const { return connected_; }

  /// Create JetStream streams (idempotent — safe to call even if they already exist).
  void ensure_streams();

  /// Publish a JSON string to a NATS subject.
  /// Returns false if not connected or on error.
  bool publish(const std::string& subject, const std::string& payload);

  /// Subscribe to a subject with a callback.
  /// The callback receives (subject, data) strings.
  using MessageCallback = std::function<void(const std::string& subject, const std::string& data)>;
  bool subscribe(const std::string& subject, MessageCallback cb);

  /// Publish a structured log event to hi.logs.agamemnon.<event> (ADR-005).
  /// Fire-and-forget: NATS failures are logged but do not propagate.
  void publish_log(const std::string& subject, const std::string& level,
                   const std::string& message, const nlohmann::json& metadata);

 private:
  std::string url_;
  void* conn_ = nullptr;  // natsConnection*  (opaque to avoid header leak)
  void* js_ = nullptr;    // jsCtx*
  bool connected_ = false;
};

}  // namespace projectagamemnon
