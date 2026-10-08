import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from organism import brain, immune
from organism.markets import load_markets
from organism.memory import Memory
from organism.organs import outreach, personalize, scoring, sourcing


class FakeResp:
    def __init__(self, data, status=200):
        self.status_code, self._data, self.text = status, data, str(data)

    def json(self):
        return self._data


class FakeSession:
    def __init__(self, pages):
        self.pages, self.calls = list(pages), []

    def post(self, url, json, headers, timeout):
        self.calls.append(json)
        return FakeResp(self.pages.pop(0))


def place(pid, name, reviews=300, rating=4.6, phone="+971 4 123 4567", web="https://x.ae", status="OPERATIONAL"):
    return {"id": pid, "displayName": {"text": name}, "internationalPhoneNumber": phone, "websiteUri": web,
            "rating": rating, "userRatingCount": reviews, "businessStatus": status,
            "regularOpeningHours": {"periods": [{"close": {"hour": 22}}] * 5}}


class OrganismTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mem = Memory(Path(self.tmp.name) / "t.db")
        self.markets = load_markets()
        self.dubai = self.markets["dubai"]
        self.ks = mock.patch.object(immune, "KILL_SWITCH", Path(self.tmp.name) / "KILL")
        self.ks.start()
        self.dd = mock.patch.object(outreach, "OUTBOX", Path(self.tmp.name) / "outbox")
        self.dd.start()

    def tearDown(self):
        self.ks.stop()
        self.dd.stop()
        self.mem.db.close()
        self.tmp.cleanup()

    def seed(self):
        pages = [{"places": [place("a", "Fade Kings Barber", 900), place("b", "Quiet Nails", 20, 3.5, web=None),
                             place("c", "Closed Spa", status="CLOSED_PERMANENTLY")], "nextPageToken": "t"},
                 {"places": [place("d", "No Phone Salon", phone=None)]}]
        session = FakeSession(pages)
        stats = sourcing.source_market(self.dubai, self.mem, api_key="k", segments=["barber"],
                                       districts=["Jumeirah"], session=session)
        return stats, session

    def test_markets_load_and_template_ignored(self):
        self.assertIn("dubai", self.markets)
        self.assertIn("riyadh", self.markets)
        self.assertNotIn("city_id", self.markets)
        self.assertTrue(self.dubai.active)
        self.assertFalse(self.markets["riyadh"].active)

    def test_sourcing_paginates_and_skips_closed(self):
        stats, session = self.seed()
        self.assertEqual(stats, {"queries": 1, "seen": 3, "new": 3})
        self.assertEqual(session.calls[1]["pageToken"], "t")
        self.assertEqual(session.calls[0]["textQuery"], "barber shop in Jumeirah, Dubai")
        # re-running dedupes
        stats2 = sourcing.source_market(self.dubai, self.mem, api_key="k", segments=["barber"],
                                        districts=["Jumeirah"], session=FakeSession([{"places": [place("a", "Fade Kings Barber")]}]))
        self.assertEqual(stats2["new"], 0)

    def test_scoring_ranks_busy_well_rated_first(self):
        self.seed()
        scoring.score_market(self.dubai, self.mem)
        ranked = [r["name"] for r in self.mem.leads(market="dubai", order_by_score=True)]
        self.assertEqual(ranked[0], "Fade Kings Barber")
        self.assertEqual(ranked[-1], "No Phone Salon")
        self.assertEqual(self.mem.lead("gplaces:d")["score"], 0)

    def test_personalize_unique_links_and_both_languages(self):
        p = personalize.personalize({"id": "gplaces:abc123", "name": "Fade Kings Barber"}, self.dubai)
        self.assertEqual(p["slug"], "fade-kings-barber-abc123")
        self.assertIn(p["demo_link"], p["copy"]["en"]["email_body"])
        self.assertIn(p["demo_link"], p["copy"]["ar"]["linkedin"])
        self.assertIn("«لا»", p["copy"]["ar"]["email_body"])

    def test_immune_blocks(self):
        self.seed()
        scoring.score_market(self.dubai, self.mem)
        lead = dict(self.mem.lead("gplaces:a"))
        self.assertIn("verify-links", immune.check(lead, self.dubai, "whatsapp", self.mem).reason)
        lead["demo_verified"] = 1
        self.assertIn("mark-tested", immune.check(lead, self.dubai, "whatsapp", self.mem).reason)
        lead["call_tested"] = 1
        # cold whatsapp is blocked without opt-in
        self.assertFalse(immune.check(lead, self.dubai, "whatsapp", self.mem))
        lead["whatsapp_opt_in"] = 1
        self.assertTrue(immune.check(lead, self.dubai, "whatsapp", self.mem))
        # opt-out wins over everything, on any channel
        self.mem.suppress("+971 4 123 4567")
        self.assertIn("not to be contacted", immune.check(lead, self.dubai, "linkedin", self.mem).reason)
        # kill switch
        immune.set_kill_switch(True)
        self.assertIn("kill", immune.check(lead, self.dubai, "whatsapp", self.mem).reason)
        immune.set_kill_switch(False)
        # inactive market
        self.assertFalse(immune.check(lead, self.markets["riyadh"], "email", self.mem))

    def test_cadence_five_touches_then_archive(self):
        self.seed()
        lead = dict(self.mem.lead("gplaces:a"), demo_verified=1, call_tested=1)
        t0 = 1_760_000_000
        day = 86400
        for n, d in enumerate([0, 3, 7, 11, 14]):
            if n:
                self.assertIn("not due", immune.check(lead, self.dubai, "linkedin", self.mem, now=t0 + (d - 1) * day).reason)
            self.assertTrue(immune.check(lead, self.dubai, "linkedin", self.mem, now=t0 + d * day))
            self.mem.record("dubai", "contacted", lead_id=lead["id"], channel="linkedin", ts=t0 + d * day)
        self.assertIn("archived", immune.check(lead, self.dubai, "linkedin", self.mem, now=t0 + 30 * day).reason)
        self.assertTrue(immune.check(lead, self.dubai, "linkedin", self.mem, now=t0 + 105 * day))
        # once they reply, Ahmad handles it personally
        self.mem.record("dubai", "replied", lead_id=lead["id"])
        lead["stage"] = "replied"
        self.assertIn("personally", immune.check(lead, self.dubai, "linkedin", self.mem, now=t0 + 105 * day).reason)

    def test_daily_cap_five_across_channels(self):
        now = 1_760_000_000
        for i in range(7):
            self.mem.upsert_lead({"id": f"x{i}", "market": "dubai", "name": f"x{i}", "phone": f"+9715000{i}"})
            self.mem.update_lead(f"x{i}", demo_verified=1, call_tested=1, demo_link="https://vocaris.ai/demo/x", score=1)
        res = outreach.run(self.dubai, "linkedin", self.mem, limit=10, now=now)
        self.assertEqual(res["drafted"], 5)
        self.assertIn("daily limit 5", res["items"][-1][2])
        self.assertEqual(outreach.run(self.dubai, "call_list", self.mem, limit=10, now=now + 60)["drafted"], 0)

    def test_call_hours(self):
        self.seed()
        lead = dict(self.mem.lead("gplaces:a"), demo_verified=1, call_tested=1)
        noon_dubai = 1_760_000_000 - (1_760_000_000 % 86400) + 8 * 3600   # 08:00 UTC = 12:00 Dubai
        self.assertTrue(immune.check(lead, self.dubai, "call_list", self.mem, now=noon_dubai))
        self.assertFalse(immune.check(lead, self.dubai, "call_list", self.mem, now=noon_dubai + 10 * 3600))

    def test_outreach_only_drafts_tested_live_demos(self):
        self.seed()
        scoring.score_market(self.dubai, self.mem)
        personalize.personalize_market(self.dubai, self.mem)
        live = {"fade-kings-barber-a"}
        class S:
            def get(self, url, timeout):
                return type("R", (), {"status_code": 200 if url.rsplit("/", 1)[1] in live else 404})()
        self.assertEqual(personalize.verify_market(self.dubai, self.mem, S()), {"checked": 3, "live": 1})
        self.assertEqual(outreach.run(self.dubai, "linkedin", self.mem)["drafted"], 0)   # not call-tested yet
        self.mem.update_lead("gplaces:a", call_tested=1)
        res = outreach.run(self.dubai, "linkedin", self.mem)
        self.assertEqual([i[0] for i in res["items"] if i[1] == "DRAFTED"], ["Fade Kings Barber"])
        draft = Path(res["files"][0]).read_text()
        self.assertIn("https://vocaris.ai/demo/fade-kings-barber-a", draft)
        self.assertIn("شهر مجاني، بدون بطاقة", draft)          # Arabic first for Dubai
        self.assertEqual(self.mem.count_events("dubai", "contacted"), 0)   # drafting is not sending

    def test_templates_have_no_banned_claims(self):
        for lang, tpl in personalize.TEMPLATES.items():
            for key, text in tpl.items():
                self.assertEqual(personalize.banned_phrases(text), [], (lang, key))
        self.assertTrue(personalize.banned_phrases("We answer every call, guaranteed"))

    def test_stage_moves_forward_only(self):
        self.seed()
        self.mem.record("dubai", "trial", lead_id="gplaces:a")
        self.mem.record("dubai", "contacted", lead_id="gplaces:a")
        self.assertEqual(self.mem.lead("gplaces:a")["stage"], "trial")

    def test_brain_shifts_capacity_to_winning_arm(self):
        self.seed()
        now = time.time()
        for i in range(40):
            lid = f"x{i}"
            self.mem.upsert_lead({"id": lid, "market": "dubai", "name": lid})
            ch = "email" if i < 20 else "call_list"
            self.mem.record("dubai", "contacted", lead_id=lid, channel=ch, ts=now)
            if ch == "call_list" and i % 2 == 0:
                self.mem.record("dubai", "trial", lead_id=lid, ts=now)
        arms = {a["channel"]: a for a in brain.allocate(self.markets, self.mem, capacity=100)}
        self.assertGreater(arms["call_list"]["allocated"], arms["email"]["allocated"])
        self.assertEqual(arms["call_list"]["trials"], 10)
        self.assertNotIn("riyadh", {a["market"] for a in arms.values()})

    def test_import_csv(self):
        path = Path(self.tmp.name) / "l.csv"
        path.write_text("Name,Phone,Email,Rating,Reviews,Area\nGlow Salon,+97150111,info@glow.ae,4.8,210,JLT\n")
        self.assertEqual(sourcing.import_csv(path, self.dubai, self.mem), {"rows": 1, "new": 1})
        self.assertEqual(self.mem.leads(market="dubai")[0]["district"], "JLT")

    def test_find_business_email_only_generic(self):
        class S:
            def get(self, *a, **k):
                return type("R", (), {"text": "ahmed.k@glow.ae booking@glow.ae logo@2x.png"})()
        self.assertEqual(sourcing.find_business_email("https://glow.ae", S()), "booking@glow.ae")


if __name__ == "__main__":
    unittest.main()
