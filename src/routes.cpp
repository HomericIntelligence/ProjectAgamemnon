// ProjectAgamemnon route handlers — C++20 skeleton
// Each handler returns the correct JSON shape with hardcoded/stub data.
// TODO markers indicate where real business logic should be implemented.

#include "projectagamemnon/routes.hpp"

#include <string>
#include "httplib.h"
#include "nlohmann/json.hpp"

namespace projectagamemnon {

using json = nlohmann::json;

void register_routes(httplib::Server& server) {
  // ── Health ────────────────────────────────────────────────────────────────

  server.Get("/v1/health", [](const httplib::Request& /*req*/, httplib::Response& res) {
    // TODO: check internal service health
    res.set_content(json{{"status", "ok"}}.dump(), "application/json");
  });

  // ── Agents ───────────────────────────────────────────────────────────────

  server.Get("/v1/agents", [](const httplib::Request& /*req*/, httplib::Response& res) {
    // TODO: return agents from backing store (GitHub Issues/Projects)
    res.set_content(json{{"agents", json::array()}}.dump(), "application/json");
  });

  server.Get("/v1/agents/by-name/(.*)",
             [](const httplib::Request& req, httplib::Response& res) {
               // TODO: look up agent by name in backing store
               const std::string name = req.matches[1];
               res.status = 404;
               res.set_content(json{{"detail", "Agent not found: " + name}}.dump(),
                               "application/json");
             });

  server.Get("/v1/agents/(.*)", [](const httplib::Request& req, httplib::Response& res) {
    // TODO: look up agent by ID in backing store
    const std::string agent_id = req.matches[1];
    res.status = 404;
    res.set_content(json{{"detail", "Agent not found: " + agent_id}}.dump(), "application/json");
  });

  server.Post("/v1/agents/docker",
              [](const httplib::Request& req, httplib::Response& res) {
                // TODO: provision docker agent via Nomad/Podman
                const auto body = json::parse(req.body, nullptr, false);
                if (body.is_discarded()) {
                  res.status = 400;
                  res.set_content(json{{"detail", "Invalid JSON"}}.dump(), "application/json");
                  return;
                }
                res.status = 501;
                res.set_content(
                    json{{"detail", "Docker agent provisioning not yet implemented"}}.dump(),
                    "application/json");
              });

  server.Post("/v1/agents", [](const httplib::Request& req, httplib::Response& res) {
    // TODO: create agent in backing store (GitHub Issue), publish to NATS
    const auto body = json::parse(req.body, nullptr, false);
    if (body.is_discarded()) {
      res.status = 400;
      res.set_content(json{{"detail", "Invalid JSON"}}.dump(), "application/json");
      return;
    }
    res.status = 501;
    res.set_content(json{{"detail", "Agent creation not yet implemented"}}.dump(),
                    "application/json");
  });

  server.Patch("/v1/agents/(.*)", [](const httplib::Request& req, httplib::Response& res) {
    // TODO: update agent fields in backing store
    const std::string agent_id = req.matches[1];
    res.status = 501;
    res.set_content(json{{"detail", "PATCH not yet implemented for: " + agent_id}}.dump(),
                    "application/json");
  });

  server.Delete("/v1/agents/(.*)", [](const httplib::Request& req, httplib::Response& res) {
    // TODO: delete agent from backing store, publish to NATS
    const std::string agent_id = req.matches[1];
    res.status = 501;
    res.set_content(json{{"detail", "DELETE not yet implemented for: " + agent_id}}.dump(),
                    "application/json");
  });

  server.Post("/v1/agents/(.*)/start",
              [](const httplib::Request& req, httplib::Response& res) {
                // TODO: wake agent (start tmux session or docker container)
                const std::string agent_id = req.matches[1];
                res.status = 501;
                res.set_content(
                    json{{"detail", "Agent start not yet implemented: " + agent_id}}.dump(),
                    "application/json");
              });

  server.Post("/v1/agents/(.*)/stop",
              [](const httplib::Request& req, httplib::Response& res) {
                // TODO: hibernate agent
                const std::string agent_id = req.matches[1];
                res.status = 501;
                res.set_content(
                    json{{"detail", "Agent stop not yet implemented: " + agent_id}}.dump(),
                    "application/json");
              });

  // ── Teams ────────────────────────────────────────────────────────────────

  server.Post("/v1/teams", [](const httplib::Request& req, httplib::Response& res) {
    // TODO: create team in backing store
    const auto body = json::parse(req.body, nullptr, false);
    if (body.is_discarded()) {
      res.status = 400;
      res.set_content(json{{"detail", "Invalid JSON"}}.dump(), "application/json");
      return;
    }
    res.status = 501;
    res.set_content(json{{"detail", "Team creation not yet implemented"}}.dump(),
                    "application/json");
  });

  server.Put("/v1/teams/(.*)", [](const httplib::Request& req, httplib::Response& res) {
    // TODO: update team members
    const std::string team_id = req.matches[1];
    res.status = 501;
    res.set_content(json{{"detail", "Team update not yet implemented: " + team_id}}.dump(),
                    "application/json");
  });

  server.Delete("/v1/teams/(.*)", [](const httplib::Request& req, httplib::Response& res) {
    // TODO: delete team
    const std::string team_id = req.matches[1];
    res.status = 501;
    res.set_content(json{{"detail", "Team delete not yet implemented: " + team_id}}.dump(),
                    "application/json");
  });

  server.Post("/v1/teams/(.*)/tasks",
              [](const httplib::Request& req, httplib::Response& res) {
                // TODO: create task in backing store (GitHub Issue), dispatch to NATS myrmidon queue
                const std::string team_id = req.matches[1];
                const auto body = json::parse(req.body, nullptr, false);
                if (body.is_discarded()) {
                  res.status = 400;
                  res.set_content(json{{"detail", "Invalid JSON"}}.dump(), "application/json");
                  return;
                }
                res.status = 501;
                res.set_content(
                    json{{"detail", "Task creation not yet implemented for team: " + team_id}}
                        .dump(),
                    "application/json");
              });

  server.Put("/v1/teams/(.*)/tasks/(.*)",
             [](const httplib::Request& req, httplib::Response& res) {
               // TODO: update task status
               const std::string team_id = req.matches[1];
               const std::string task_id = req.matches[2];
               res.status = 501;
               res.set_content(
                   json{{"detail",
                         "Task update not yet implemented: " + team_id + "/" + task_id}}
                       .dump(),
                   "application/json");
             });

  server.Get("/v1/teams/(.*)/tasks",
             [](const httplib::Request& req, httplib::Response& res) {
               // TODO: list tasks for team from backing store
               res.set_content(json{{"tasks", json::array()}}.dump(), "application/json");
             });

  // ── Tasks (global) ───────────────────────────────────────────────────────

  server.Get("/v1/tasks", [](const httplib::Request& /*req*/, httplib::Response& res) {
    // TODO: list all tasks from backing store
    res.set_content(json{{"tasks", json::array()}}.dump(), "application/json");
  });

  // ── Workflows ────────────────────────────────────────────────────────────

  server.Get("/v1/workflows", [](const httplib::Request& /*req*/, httplib::Response& res) {
    // TODO: list active workflows
    res.set_content(json{{"workflows", json::array()}}.dump(), "application/json");
  });

  // ── Chaos (ProjectCharybdis integration) ─────────────────────────────────

  server.Post("/v1/chaos/network-partition",
              [](const httplib::Request& /*req*/, httplib::Response& res) {
                // TODO: inject Tailscale network partition
                res.set_content(
                    json{{"id", "fault-stub"}, {"type", "network-partition"}, {"status", "active"}}
                        .dump(),
                    "application/json");
              });

  server.Post("/v1/chaos/latency",
              [](const httplib::Request& /*req*/, httplib::Response& res) {
                // TODO: inject network latency via tc netem
                res.set_content(
                    json{{"id", "fault-stub"}, {"type", "latency"}, {"status", "active"}}.dump(),
                    "application/json");
              });

  server.Post("/v1/chaos/kill",
              [](const httplib::Request& /*req*/, httplib::Response& res) {
                // TODO: kill named service via Nomad/systemd
                res.set_content(
                    json{{"id", "fault-stub"}, {"type", "kill"}, {"status", "active"}}.dump(),
                    "application/json");
              });

  server.Post("/v1/chaos/queue-starve",
              [](const httplib::Request& /*req*/, httplib::Response& res) {
                // TODO: stall NATS pull consumers
                res.set_content(
                    json{{"id", "fault-stub"}, {"type", "queue-starve"}, {"status", "active"}}
                        .dump(),
                    "application/json");
              });

  server.Delete("/v1/chaos/(.*)", [](const httplib::Request& req, httplib::Response& res) {
    // TODO: remove injected fault
    const std::string fault_id = req.matches[1];
    res.set_content(json{{"status", "removed"}, {"id", fault_id}}.dump(), "application/json");
  });
}

}  // namespace projectagamemnon
