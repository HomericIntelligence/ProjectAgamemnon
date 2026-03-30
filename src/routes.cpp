#include "projectagamemnon/routes.hpp"

#include "projectagamemnon/nats_client.hpp"
#include "projectagamemnon/store.hpp"

// cpp-httplib — single-header, no SSL needed for internal mesh traffic
#define CPPHTTPLIB_NO_EXCEPTIONS
#include "httplib.h"

#include "nlohmann/json.hpp"

#include <iostream>
#include <string>

namespace projectagamemnon {

using json = nlohmann::json;

// ── Helpers ───────────────────────────────────────────────────────────────────

static void reply_json(httplib::Response& res, int status, const json& body) {
  res.status = status;
  res.set_content(body.dump(), "application/json");
}

static void reply_not_found(httplib::Response& res, const std::string& what) {
  reply_json(res, 404, {{"error", what + " not found"}});
}

static void reply_bad_request(httplib::Response& res, const std::string& msg) {
  reply_json(res, 400, {{"error", msg}});
}

/// Parse JSON body; returns false and sets 400 on parse error.
static bool parse_body(const httplib::Request& req, httplib::Response& res, json& out) {
  if (req.body.empty()) { out = json::object(); return true; }
  try {
    out = json::parse(req.body);
    return true;
  } catch (const json::parse_error& e) {
    reply_bad_request(res, std::string("invalid JSON: ") + e.what());
    return false;
  }
}

// ── Route registration ────────────────────────────────────────────────────────

// NOTE: We capture Store* and NatsClient* (raw pointers, not references) to
// avoid dangling-reference UB when the lambda outlives register_routes' stack.
// Both store and nats are owned by main() and outlive the server.

void register_routes(httplib::Server& server, Store& store, NatsClient& nats) {
  Store*       sp = &store;
  NatsClient*  np = &nats;

  // ── Health / version ────────────────────────────────────────────────────
  server.Get("/health", [](const httplib::Request&, httplib::Response& res) {
    reply_json(res, 200, {{"status", "ok"}, {"service", "ProjectAgamemnon"}});
  });

  server.Get("/v1/health", [](const httplib::Request&, httplib::Response& res) {
    reply_json(res, 200, {{"status", "ok"}});
  });

  server.Get("/v1/version", [](const httplib::Request&, httplib::Response& res) {
    reply_json(res, 200, {{"version", "0.1.0"}, {"name", "ProjectAgamemnon"}});
  });

  // ── Agents ──────────────────────────────────────────────────────────────

  // GET /v1/agents
  server.Get("/v1/agents", [sp](const httplib::Request&, httplib::Response& res) {
    reply_json(res, 200, sp->list_agents());
  });

  // POST /v1/agents
  server.Post("/v1/agents", [sp, np](const httplib::Request& req, httplib::Response& res) {
    json body;
    if (!parse_body(req, res, body)) return;
    json result = sp->create_agent(body);
    np->publish("hi.agents.created", result.dump());
    reply_json(res, 201, result);
  });

  // POST /v1/agents/:id/start  — registered BEFORE the generic :id route
  server.Post(R"(/v1/agents/([^/]+)/start)",
    [sp, np](const httplib::Request& req, httplib::Response& res) {
      std::string id = req.matches[1];
      json result = sp->start_agent(id);
      if (result.is_null()) { reply_not_found(res, "agent"); return; }
      np->publish("hi.agents.started", result.dump());
      reply_json(res, 200, result);
    });

  // POST /v1/agents/:id/stop
  server.Post(R"(/v1/agents/([^/]+)/stop)",
    [sp, np](const httplib::Request& req, httplib::Response& res) {
      std::string id = req.matches[1];
      json result = sp->stop_agent(id);
      if (result.is_null()) { reply_not_found(res, "agent"); return; }
      np->publish("hi.agents.stopped", result.dump());
      reply_json(res, 200, result);
    });

  // GET /v1/agents/:id
  server.Get(R"(/v1/agents/([^/]+))",
    [sp](const httplib::Request& req, httplib::Response& res) {
      std::string id = req.matches[1];
      json agent = sp->get_agent(id);
      if (agent.is_null()) { reply_not_found(res, "agent"); return; }
      reply_json(res, 200, {{"agent", agent}});
    });

  // PATCH /v1/agents/:id
  server.Patch(R"(/v1/agents/([^/]+))",
    [sp, np](const httplib::Request& req, httplib::Response& res) {
      std::string id = req.matches[1];
      json body;
      if (!parse_body(req, res, body)) return;
      json result = sp->update_agent(id, body);
      if (result.is_null()) { reply_not_found(res, "agent"); return; }
      np->publish("hi.agents.updated", result.dump());
      reply_json(res, 200, {{"agent", result}});
    });

  // DELETE /v1/agents/:id
  server.Delete(R"(/v1/agents/([^/]+))",
    [sp, np](const httplib::Request& req, httplib::Response& res) {
      std::string id = req.matches[1];
      if (!sp->delete_agent(id)) { reply_not_found(res, "agent"); return; }
      np->publish("hi.agents.deleted", json{{"id", id}}.dump());
      reply_json(res, 200, {{"deleted", id}});
    });

  // ── Teams ────────────────────────────────────────────────────────────────

  // GET /v1/teams
  server.Get("/v1/teams", [sp](const httplib::Request&, httplib::Response& res) {
    reply_json(res, 200, sp->list_teams());
  });

  // POST /v1/teams
  server.Post("/v1/teams", [sp, np](const httplib::Request& req, httplib::Response& res) {
    json body;
    if (!parse_body(req, res, body)) return;
    json result = sp->create_team(body);
    np->publish("hi.agents.team.created", result.dump());
    reply_json(res, 201, result);
  });

  // GET /v1/teams/:id
  server.Get(R"(/v1/teams/([^/]+))",
    [sp](const httplib::Request& req, httplib::Response& res) {
      std::string id = req.matches[1];
      json team = sp->get_team(id);
      if (team.is_null()) { reply_not_found(res, "team"); return; }
      reply_json(res, 200, {{"team", team}});
    });

  // PUT /v1/teams/:id
  server.Put(R"(/v1/teams/([^/]+))",
    [sp, np](const httplib::Request& req, httplib::Response& res) {
      std::string id = req.matches[1];
      json body;
      if (!parse_body(req, res, body)) return;
      json result = sp->update_team(id, body);
      if (result.is_null()) { reply_not_found(res, "team"); return; }
      np->publish("hi.agents.team.updated", result.dump());
      reply_json(res, 200, {{"team", result}});
    });

  // DELETE /v1/teams/:id
  server.Delete(R"(/v1/teams/([^/]+))",
    [sp, np](const httplib::Request& req, httplib::Response& res) {
      std::string id = req.matches[1];
      if (!sp->delete_team(id)) { reply_not_found(res, "team"); return; }
      np->publish("hi.agents.team.deleted", json{{"id", id}}.dump());
      reply_json(res, 200, {{"deleted", id}});
    });

  // ── Tasks ────────────────────────────────────────────────────────────────

  // GET /v1/tasks  (all tasks across all teams)
  server.Get("/v1/tasks", [sp](const httplib::Request&, httplib::Response& res) {
    reply_json(res, 200, sp->list_all_tasks());
  });

  // GET /v1/teams/:team_id/tasks — registered BEFORE the generic :team_id route
  server.Get(R"(/v1/teams/([^/]+)/tasks)",
    [sp](const httplib::Request& req, httplib::Response& res) {
      std::string team_id = req.matches[1];
      reply_json(res, 200, sp->list_tasks_for_team(team_id));
    });

  // POST /v1/teams/:team_id/tasks
  server.Post(R"(/v1/teams/([^/]+)/tasks)",
    [sp, np](const httplib::Request& req, httplib::Response& res) {
      std::string team_id = req.matches[1];
      json body;
      if (!parse_body(req, res, body)) return;
      json result = sp->create_task(team_id, body);
      np->publish("hi.tasks.created", result.dump());
      reply_json(res, 201, result);
    });

  // GET /v1/teams/:team_id/tasks/:task_id
  server.Get(R"(/v1/teams/([^/]+)/tasks/([^/]+))",
    [sp](const httplib::Request& req, httplib::Response& res) {
      std::string team_id = req.matches[1];
      std::string task_id = req.matches[2];
      json task = sp->get_task(team_id, task_id);
      if (task.is_null()) { reply_not_found(res, "task"); return; }
      reply_json(res, 200, {{"task", task}});
    });

  // PATCH /v1/teams/:team_id/tasks/:task_id
  server.Patch(R"(/v1/teams/([^/]+)/tasks/([^/]+))",
    [sp, np](const httplib::Request& req, httplib::Response& res) {
      std::string team_id = req.matches[1];
      std::string task_id = req.matches[2];
      json body;
      if (!parse_body(req, res, body)) return;
      json result = sp->update_task(team_id, task_id, body);
      if (result.is_null()) { reply_not_found(res, "task"); return; }
      np->publish("hi.tasks.updated", result.dump());
      reply_json(res, 200, {{"task", result}});
    });

  // ── Chaos ────────────────────────────────────────────────────────────────

  // GET /v1/chaos
  server.Get("/v1/chaos", [sp](const httplib::Request&, httplib::Response& res) {
    reply_json(res, 200, sp->list_faults());
  });

  // POST /v1/chaos/:type
  server.Post(R"(/v1/chaos/([^/]+))",
    [sp, np](const httplib::Request& req, httplib::Response& res) {
      std::string type = req.matches[1];
      json result = sp->create_fault(type);
      np->publish("hi.agents.chaos.injected", result.dump());
      reply_json(res, 201, result);
    });

  // DELETE /v1/chaos/:id
  server.Delete(R"(/v1/chaos/([^/]+))",
    [sp, np](const httplib::Request& req, httplib::Response& res) {
      std::string id = req.matches[1];
      if (!sp->remove_fault(id)) { reply_not_found(res, "fault"); return; }
      np->publish("hi.agents.chaos.removed", json{{"id", id}}.dump());
      reply_json(res, 200, {{"deleted", id}});
    });

  std::cout << "[agamemnon] routes registered\n";
}

}  // namespace projectagamemnon
