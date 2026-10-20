"""Tests for stage3_candidate_docs.py on hand-built events and task texts (expected values by hand)."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage3_candidate_docs as cd  # noqa: E402


def ev(i, acct, ts, svc, action, args=None, meta=None, exit_code=0, task="t"):
    return {"_ord": i, "account": acct, "ts": ts, "service": svc, "action": action,
            "args": args or {}, "result_meta": meta or {}, "exit_code": exit_code, "task_id": task}


# ---- bank side -------------------------------------------------------------------

def test_paths_split_shared_and_ws():
    t = "Update the shared `infra/training-pipeline/README.md` and infra/x/{ws}/README.md today."
    assert cd.shared_paths(t) == ["infra/training-pipeline/README.md"]
    assert cd.ws_paths(t) == ["infra/x/{ws}/README.md"]


def test_classify_doc_task():
    doc = "monitoring/prometheus/model-registry.json"
    assert cd.classify_doc_task(f"Add a new Grafana panel using metrics from {doc}.", doc) == "read"
    doc2 = "infra/training-pipeline/README.md"
    assert cd.classify_doc_task(f"Update the deployment section of the shared `{doc2}`.", doc2) == "write"
    doc3 = "/legal/templates/msa.md"
    assert cd.classify_doc_task(f"Review a clause in the shared MSA template at ownCloud `{doc3}`.", doc3) == "read"
    doc4 = "/hr/policies/handbook.md"
    assert cd.classify_doc_task(f"Review and update one section of the shared handbook at `{doc4}`.", doc4) == "write"
    doc5 = "eval/red-team-suite/.gitlab-ci.yml"
    assert cd.classify_doc_task(f"Review the open MR touching the shared `{doc5}` and confirm CI passes.", doc5) == "read"


def test_p_any_in_session_hand():
    # one task among 10, k uniform on {2,3,4}: P = mean(k/10) = 0.3
    assert math.isclose(cd.p_any_in_session(10, 1), 0.3)
    # m = 0 never drawn
    assert cd.p_any_in_session(10, 0) == 0.0
    # day of 2 sessions: 1 - 0.7^2
    assert math.isclose(cd.p_any_in_day(10, 1, 2), 1 - 0.7 ** 2)


def test_doc_rates_hand():
    r = cd.doc_rates(n=10, team_size=4, m_write=1, m_read=0, s=1)
    assert math.isclose(r.exp_writers, 4 * 0.3)
    assert math.isclose(r.exp_write_draws, 4 * 1 * 1 * 3 / 10)
    assert r.exp_pure_readers == 0.0 and r.p_day_any_pure_reader == 0.0
    assert math.isclose(r.p_day_any_writer, 1 - 0.7 ** 4)
    r2 = cd.doc_rates(n=10, team_size=1, m_write=1, m_read=1, s=1)
    # pure reader: no write and at least one of the read: P(no w) - P(neither)
    pw = 0.3
    pall = cd.p_any_in_session(10, 2)
    assert math.isclose(r2.exp_pure_readers, (1 - pw) - (1 - pall))


def test_bank_candidates_groups_teams():
    bank = {"platform": {"team": "platform", "variants": [
        "Update the shared `a/README.md`.", "Review the latest change to the shared `a/README.md`.",
        "Edit x/{ws}/notes.md."]}}
    out = cd.bank_candidates(bank, {"platform": 3})
    (doc,) = out["docs"]
    assert doc["doc"] == "a/README.md" and doc["n_write_tasks"] == 1 and doc["n_read_tasks"] == 1
    assert out["ws_tasks_by_team"] == {"platform": 1}


# ---- prefix side -----------------------------------------------------------------

def test_resource_of_forms():
    assert cd.resource_of(ev(0, "a", "2026-04-06T07:00:00Z", "plane", "get_issue", {"ticket_id": "ops-2"})) == ("issue", "OPS-2")
    assert cd.resource_of(ev(0, "a", "2026-04-06T07:00:00Z", "plane", "create_issue", {}, {"id": "INFRA-3"})) == ("issue", "INFRA-3")
    assert cd.resource_of(ev(0, "a", "2026-04-06T07:00:00Z", "eval_server", "submit_eval",
                             {"config_id": "release-gate"})) == ("config", "release-gate")
    assert cd.resource_of(ev(0, "a", "2026-04-06T07:00:00Z", "model_registry", "get_checkpoint",
                             {"ckpt_id": "c1"})) == ("checkpoint", "c1")
    assert cd.resource_of(ev(0, "a", "2026-04-06T07:00:00Z", "plane", "list_issues", {"project_id": "OPS"})) is None


def test_anchored():
    assert cd.is_anchored(ev(0, "a", "t", "model_registry", "deploy"))
    assert cd.is_anchored(ev(0, "a", "t", "plane", "transition_issue", {"state": "Approved"}))
    assert cd.is_anchored(ev(0, "a", "t", "plane", "update_issue", {"patch": {"state": "approved"}}))
    assert not cd.is_anchored(ev(0, "a", "t", "plane", "update_issue", {"patch": {"state": "done"}}))
    assert not cd.is_anchored(ev(0, "a", "t", "eval_server", "update_config"))


D1, D2 = "2026-04-06T08:00:00Z", "2026-04-07T08:00:00Z"
EVENTS = [
    ev(0, "w1", D1, "plane", "create_issue", {"name": "Raise cap", "description": "set cap_score_min to 0.65"},
       {"id": "INFRA-1"}, task="tw1"),
    ev(1, "r1", D1, "plane", "get_issue", {"issue_id": "INFRA-1"}, task="tr1"),
    ev(2, "r1", D1, "eval_server", "update_config", {"config_id": "release-gate", "config": "{\"cap\": 0.65}"},
       task="tr1"),
    ev(3, "r2", D1, "plane", "get_issue", {"issue_id": "INFRA-1"}, task="tr2"),
    ev(4, "r2", D1, "model_registry", "deploy", {"checkpoint_id": "c1"}, task="tr2"),
    ev(5, "w2", D2, "plane", "add_comment", {"issue_id": "INFRA-1", "body": "agreed"}, task="tw2"),
    ev(6, "w2", D2, "plane", "get_issue", {"issue_id": "INFRA-1"}, task="tw2"),
    ev(7, "r3", D2, "plane", "list_comments", {"issue_id": "INFRA-1"}, task="tr3"),
    ev(8, "r3", D2, "plane", "get_issue", {"issue_id": "INFRA-9"}, exit_code=1, task="tr3"),
]


def test_resource_stats_and_pure_readers():
    st = cd.per_resource_stats(EVENTS)
    s = cd.summarise_resource(("issue", "INFRA-1"), st[("issue", "INFRA-1")])
    assert s["writers_total"] == 2 and s["readers_total"] == 4
    assert s["per_day"]["2026-04-06"]["pure_readers"] == 2
    # w2 read and wrote on day 2, so only r3 is a pure reader
    assert s["per_day"]["2026-04-07"]["pure_readers"] == 1
    assert s["per_day"]["2026-04-07"]["participants"] == 2
    assert s["read_on_most_days"] is True
    assert cd.is_candidate(s)
    assert ("issue", "INFRA-9") not in st  # failed event ignored


def test_consumption_routes_carried():
    routes = cd.consumption_routes(EVENTS, {("issue", "INFRA-1")})
    o = routes[("issue", "INFRA-1")]
    assert o["reads"] == 4
    assert o["reads_then_offdoc_write"] == 2
    assert o["reads_then_unanchored"] == 1 and o["reads_then_anchored"] == 1
    assert o["carried_unanchored"] == 1          # 0.65 carried from the ticket into the config
    assert o["carried_anchored"] == 0            # the deploy carries no ticket token
    assert o["unanchored_actions"] == {"eval_server.update_config": 1}


def test_carry_excludes_tokens_reader_already_had():
    evs = [ev(0, "w", D1, "plane", "create_issue", {"description": "path /data/x_01"}, {"id": "P-1"}, task="a"),
           ev(1, "r", D1, "plane", "add_comment", {"issue_id": "P-2", "body": "/data/x_01"}, task="b"),
           ev(2, "r", D1, "plane", "get_issue", {"issue_id": "P-1"}, task="c"),
           ev(3, "r", D1, "secrets_store", "set_access_policy", {"key": "k", "description": "/data/x_01"}, task="c")]
    o = cd.consumption_routes(evs, {("issue", "P-1")})[("issue", "P-1")]
    assert o["reads_then_unanchored"] == 1 and o["carried_unanchored"] == 0


def test_budget_cap_and_reviewable():
    assert cd.budget_cap(0.05, 48) == 2 and cd.budget_cap(0.10, 49) == 4 and cd.budget_cap(0.05, 10) == 1
    blk = cd.participants_block({"2026-04-06": 2, "2026-04-07": 3}, {"2026-04-06": 48, "2026-04-07": 49})
    assert blk["reviewable_B0.05"] is False and blk["reviewable_B0.10"] is True


def test_p6_participants():
    p6 = cd.p6_participants(EVENTS)
    assert p6["events"]["deploy"]["per_day"]["2026-04-06"] == 1
    assert p6["events"]["eval-config write"]["per_day"]["2026-04-06"] == 1


def test_write_md_keeps_preregistration(tmp_path):
    p = tmp_path / "x.md"
    p.write_text("# T\n\nPre-registered text.\n\n<!-- RESULTS BELOW: keep -->\nold results\n")
    cd.write_md(p, "new results\n", "T")
    txt = p.read_text()
    assert "Pre-registered text." in txt and "new results" in txt and "old results" not in txt


def test_bare_name_in_ws_task_is_not_shared():
    t = "Investigate the pipeline in gitlab.com/infra/tp/{ws}/dataset-sync and patch sync_runner.py."
    assert cd.shared_paths(t) == [] and cd.ambiguous_bare_names(t) == ["sync_runner.py"]
    assert cd.shared_paths("Review the change to the shared `x/.gitlab-ci.yml`.") == ["x/.gitlab-ci.yml"]


def test_strict_tokens_drop_common_and_dates():
    share = {"0.65": 0.001, "in_progress": 0.2, "2026-04-06": 0.001, "job-7": 0.3}
    assert cd.strict_tokens({"0.65", "in_progress", "2026-04-06", "job-7"}, share) == {"0.65"}


def test_strict_carry_counted():
    share = cd.token_event_share(EVENTS)
    o = cd.consumption_routes(EVENTS, {("issue", "INFRA-1")}, share)[("issue", "INFRA-1")]
    # in this 9-event fixture every token is "common" (>0.5% of events), so strict finds none
    assert o["strict_carried_unanchored"] == 0
    o2 = cd.consumption_routes(EVENTS, {("issue", "INFRA-1")}, {})[("issue", "INFRA-1")]
    assert o2["strict_carried_unanchored"] == 1


def test_inprocess_bank_rates_and_project_rates():
    bank = {"evaluations": {"team": "evaluations", "variants": [
        "Check Plane project INFRA for a ticket; apply it with eval_server.update_config on release-gate.",
        "Open a Plane ticket in INFRA summarising the release-gate jobs.",
        "Create Plane ticket {ws}-1 about INFRA.", "Unrelated task."]}}
    out = {e["resource"]: e for e in cd.inprocess_bank_rates(bank, {"evaluations": 2})}
    rg = out["config release-gate"]
    assert [x["role"] for x in rg["tasks"]] == ["write", "read"]
    infra = out["Plane project INFRA (any ticket)"]
    assert [x["role"] for x in infra["tasks"]] == ["read", "write"]      # {ws} task excluded
    exp = cd.doc_rates(4, 2, 1, 1, 2)
    assert math.isclose(rg["rates"]["s2"]["exp_writers"], exp.exp_writers)
    st = cd.per_resource_stats(EVENTS)
    pr = cd.project_day_rates(st, "INFRA")
    assert pr == {"writers_per_day": 1.0, "pure_readers_per_day": 1.5}
    assert cd.project_of("LLAMA17-5") == "LLAMA17"
