from neighborhood_fit.score import rank, nice_to_have

def row(id, rent, minutes, nice=0.5):
    return {"neighborhood_id": id, "name": id.title(), "rent": rent, "minutes": minutes, "nice": nice}


def ids(results):
    return [r["neighborhood_id"] for r in results]


def test_hard_limits_exclude_not_downrank():
    rows = [row("a", 2000, 10), row("pricey", 3100, 5), row("far", 2000, 50)]
    assert ids(rank(rows, budget=3000, max_commute=30, hub_name="Downtown")) == ["a"]


def test_rent_equal_to_budget_is_allowed_commute_equal_to_max_is_allowed():
    rows = [row("edge", 3000, 30)]
    assert ids(rank(rows, budget=3000, max_commute=30, hub_name="Downtown")) == ["edge"]


def test_empty_when_everything_filtered():
    assert rank([row("a", 5000, 10)], budget=3000, max_commute=30, hub_name="X") == []


def test_weights_50_40_10():
    # cheapest+farthest vs priciest+closest; same nice. Weights decide.
    rows = [row("cheap", 2000, 30, 0), row("close", 3000, 0, 0)]
    res = {r["neighborhood_id"]: r for r in rank(rows, 3000, 30, "H")}
    # cheap: rent norm 1.0 -> 0.5, commute 0 -> 0.0 => 0.5
    # close: rent norm 0.0 -> 0.0, commute 1.0 -> 0.4 => 0.4
    assert res["cheap"]["score"] == 0.5
    assert res["close"]["score"] == 0.4
    assert ids(rank(rows, 3000, 30, "H")) == ["cheap", "close"]


def test_nice_to_have_contributes_10_percent():
    rows = [row("plain", 2000, 10, 0.0), row("fun", 2000, 10, 1.0)]
    res = rank(rows, 3000, 30, "H")
    assert ids(res) == ["fun", "plain"]
    assert round(res[0]["score"] - res[1]["score"], 6) == 0.1


def test_single_survivor_and_ties_are_stable():
    rows = [row("b", 2000, 10), row("a", 2000, 10)]
    res = rank(rows, 3000, 30, "H")
    assert ids(res) == ["a", "b"]  # tie broken by name
    assert res[0]["score"] == res[1]["score"]


def test_why_mentions_headroom_and_commute():
    r = rank([row("a", 2200, 18)], 3000, 30, "Downtown")[0]
    assert r["why"] == "$800 under budget, 18 min to Downtown"


def test_nice_to_have_is_mean_of_tags():
    assert nice_to_have({"walkability": 1.0, "beach": 0.0, "nightlife": 0.5}) == 0.5


def test_why_shows_less_than_one_minute_instead_of_zero():
    r = rank([row("hub", 2200, 0.0), row("near", 2200, 0.4), row("one", 2200, 0.6)], 3000, 30, "Downtown")
    why = {x["neighborhood_id"]: x["why"] for x in r}
    assert why["hub"] == "$800 under budget, <1 min to Downtown"
    assert why["near"] == "$800 under budget, <1 min to Downtown"
    assert why["one"] == "$800 under budget, 1 min to Downtown"
