from ..config import settings


def price(provider, incoming, outgoing):
    cfg = settings()
    rates = (cfg.gemini_input_per_million, cfg.gemini_output_per_million) if provider == "gemini" else (cfg.groq_input_per_million, cfg.groq_output_per_million)
    usd = (incoming * rates[0] + outgoing * rates[1]) / 1_000_000 if provider != "offline_demo" else 0
    return usd, usd * cfg.usd_to_gbp


def roi():
    return {"baseline_onboarding_days": 62, "target_days": 30, "baseline_chase_days": 5.5,
            "target_chase_days": 3.0, "rounds": 3, "cases_per_month": 400,
            "case_days_saved_monthly": (5.5-3.0)*3*400, "projection": True}
