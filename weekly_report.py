from collections import Counter
from io import BytesIO
from statistics import mean, pstdev
from datetime import timedelta

DEFAULT_WEEKLY_WEIGHTS = {
    "Daily Mood": 20.0,
    "Journal Emotion": 20.0,
    "Sentiment": 15.0,
    "Stress": 15.0,
    "Sleep": 10.0,
    "Workload": 10.0,
    "Journal Consistency": 10.0,
}

MOOD_SCORE = {"Amazing": 100.0, "Happy": 85.0, "Normal": 65.0, "Sad": 35.0, "Angry": 15.0}
EMOTION_SCORE = {"Happy": 100.0, "Joy": 100.0, "Excited": 95.0, "Calm": 90.0,
                 "Neutral": 65.0, "Sad": 35.0, "Stress": 30.0, "Angry": 20.0, "Fear": 25.0}
WORKLOAD_SCORE = {"Low": 100.0, "Medium": 70.0, "High": 35.0}


def _clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(v)))


def _sentiment_score(day):
    compound = day.get("compound_score")
    if compound is not None:
        return _clamp((float(compound) + 1.0) * 50.0)
    return MOOD_SCORE.get(day.get("sentiment"), None)


def _sleep_score(hours):
    if hours is None:
        return None
    h = float(hours)
    if 7.0 <= h <= 9.0:
        return 100.0
    if h < 7.0:
        return _clamp(100.0 - (7.0 - h) * 20.0)
    return _clamp(100.0 - (h - 9.0) * 12.5, 70.0, 100.0)


def daily_component_scores(day):
    scores = {}
    if day.get("mood"):
        scores["Daily Mood"] = MOOD_SCORE.get(day["mood"], 65.0)
    if day.get("emotion"):
        scores["Journal Emotion"] = EMOTION_SCORE.get(day["emotion"], 65.0)
    if day.get("compound_score") is not None or day.get("sentiment"):
        scores["Sentiment"] = _sentiment_score(day)
    if day.get("stress_level") is not None:
        scores["Stress"] = _clamp((10.0 - float(day["stress_level"])) * 10.0)
    if day.get("sleep_hours") is not None:
        scores["Sleep"] = _sleep_score(day["sleep_hours"])
    if day.get("workload"):
        scores["Workload"] = WORKLOAD_SCORE.get(str(day["workload"]).title(), 70.0)
    return scores


def calculate_daily_score(day, weights=None):
    weights = weights or DEFAULT_WEEKLY_WEIGHTS
    scores = daily_component_scores(day)
    usable = {k: weights.get(k, 0.0) for k in scores if scores.get(k) is not None and weights.get(k, 0.0) > 0}
    if not usable:
        return None
    total_w = sum(usable.values())
    return round(sum(scores[k] * usable[k] for k in usable) / total_w, 1)


def build_weekly_report_data(user_id, end_date, get_user_mood_history, get_daily_wellness_range):
    start_date = end_date - timedelta(days=6)
    mood_rows = [r for r in get_user_mood_history(user_id, limit=5000)
                 if start_date <= r["mood_date"] <= end_date]
    wellness_rows = get_daily_wellness_range(user_id, start_date, end_date)
    wellness_by_date = {r["wellness_date"]: r for r in wellness_rows}
    days = []
    for offset in range(7):
        d = start_date + timedelta(days=offset)
        rows = [r for r in mood_rows if r["mood_date"] == d]
        manual_rows = [r for r in rows if r.get("source") == "manual"]
        nlp_rows = [r for r in rows if r.get("source") == "nlp" or r.get("emotion")]
        manual_latest = manual_rows[0] if manual_rows else None
        nlp_latest = nlp_rows[0] if nlp_rows else None
        latest = nlp_latest or (rows[0] if rows else None)
        journal_rows = [r for r in nlp_rows if r.get("journal_text") and r["journal_text"].strip()]
        w = wellness_by_date.get(d) or {}
        day = {
            "date": d,
            # Prefer the employee's explicitly selected mood over an NLP-derived mood.
            "mood": manual_latest.get("sentiment") if manual_latest else (latest.get("sentiment") if latest else None),
            "emotion": nlp_latest.get("emotion") if nlp_latest else None,
            "emotion_confidence": nlp_latest.get("confidence") if nlp_latest else None,
            "sentiment": nlp_latest.get("sentiment") if nlp_latest else None,
            "compound_score": nlp_latest.get("compound_score") if nlp_latest else None,
            "positive_score": nlp_latest.get("positive_score") if nlp_latest else None,
            "negative_score": nlp_latest.get("negative_score") if nlp_latest else None,
            "neutral_score": nlp_latest.get("neutral_score") if nlp_latest else None,
            "journal_text": journal_rows[0].get("journal_text") if journal_rows else None,
            "stress_level": w.get("stress_level"),
            "sleep_hours": w.get("sleep_hours"),
            "workload": w.get("workload"),
            "has_wellness_data": bool(latest or w),
            "has_journal": bool(journal_rows),
        }
        days.append(day)
    return {"start_date": start_date, "end_date": end_date, "days": days}


def aggregate_week(days, weights):
    available_days = [d for d in days if d["has_wellness_data"]]
    coverage = len(available_days) / 7.0 * 100.0
    journal_days = sum(1 for d in days if d["has_journal"])
    consistency = journal_days / 7.0 * 100.0

    component_values = {k: [] for k in weights}
    daily_scores = []
    for d in days:
        scores = daily_component_scores(d)
        d["component_scores"] = scores
        d["daily_score"] = calculate_daily_score(d, weights)
        if d["daily_score"] is not None:
            daily_scores.append((d["date"], d["daily_score"]))
        for k, v in scores.items():
            component_values.setdefault(k, []).append(v)
    component_values["Journal Consistency"] = [consistency]

    usable = {k: mean(v) for k, v in component_values.items() if v}
    active_weights = {k: weights.get(k, 0.0) for k in usable if weights.get(k, 0.0) > 0}
    weight_sum = sum(active_weights.values())
    weekly_score = round(sum(usable[k] * active_weights[k] for k in active_weights) / weight_sum, 1) if weight_sum else None

    stress_values = [float(d["stress_level"]) for d in days if d["stress_level"] is not None]
    sleep_values = [float(d["sleep_hours"]) for d in days if d["sleep_hours"] is not None]
    workload_values = [d["workload"] for d in days if d["workload"]]
    mood_values = [d["mood"] for d in days if d["mood"]]
    emotion_values = [d["emotion"] for d in days if d["emotion"]]
    positive_scores = [float(d["positive_score"]) for d in days if d["positive_score"] is not None]
    negative_scores = [float(d["negative_score"]) for d in days if d["negative_score"] is not None]
    neutral_scores = [float(d["neutral_score"]) for d in days if d["neutral_score"] is not None]
    compounds = [float(d["compound_score"]) for d in days if d["compound_score"] is not None]
    conf_values = [float(d["emotion_confidence"]) for d in days if d["emotion_confidence"] is not None]

    trend_stress = None
    if len(stress_values) >= 2:
        first = next(d["stress_level"] for d in days if d["stress_level"] is not None)
        last = next(d["stress_level"] for d in reversed(days) if d["stress_level"] is not None)
        trend_stress = "increasing" if last > first + 0.5 else "decreasing" if last < first - 0.5 else "stable"

    workload_counts = dict(Counter(str(x).title() for x in workload_values))
    emotion_counts = dict(Counter(emotion_values))
    mood_counts = dict(Counter(mood_values))
    sentiment_counts = dict(Counter(d["sentiment"] for d in days if d.get("sentiment")))

    return {
        "coverage_days": len(available_days), "coverage_pct": round(coverage, 2),
        "journal_days": journal_days, "journal_consistency": round(consistency, 2),
        "weekly_score": weekly_score, "daily_scores": daily_scores,
        "component_averages": usable,
        "avg_stress": mean(stress_values) if stress_values else None,
        "min_stress": min(stress_values) if stress_values else None,
        "max_stress": max(stress_values) if stress_values else None,
        "stress_trend": trend_stress,
        "avg_sleep": mean(sleep_values) if sleep_values else None,
        "min_sleep": min(sleep_values) if sleep_values else None,
        "max_sleep": max(sleep_values) if sleep_values else None,
        "sleep_consistency": round(100.0 - (pstdev(sleep_values) * 20.0), 1) if len(sleep_values) > 1 else (100.0 if sleep_values else None),
        "avg_workload": (sum(WORKLOAD_SCORE.get(str(x).title(), 70.0) for x in workload_values) / len(workload_values)) if workload_values else None,
        "high_workload_days": sum(1 for x in workload_values if str(x).title() == "High"),
        "workload_counts": workload_counts,
        "mood_counts": mood_counts,
        "emotion_counts": emotion_counts,
        "sentiment_counts": sentiment_counts,
        "most_common_mood": Counter(mood_values).most_common(1)[0][0] if mood_values else None,
        "most_common_emotion": Counter(emotion_values).most_common(1)[0][0] if emotion_values else None,
        "positive_emotion_days": sum(v for k, v in emotion_counts.items() if k in {"Happy", "Joy", "Excited", "Calm"}),
        "negative_emotion_days": sum(v for k, v in emotion_counts.items() if k in {"Sad", "Stress", "Angry", "Fear"}),
        "avg_emotion_confidence": mean(conf_values) if conf_values else None,
        "avg_positive": mean(positive_scores) if positive_scores else None,
        "avg_negative": mean(negative_scores) if negative_scores else None,
        "avg_neutral": mean(neutral_scores) if neutral_scores else None,
        "avg_compound": mean(compounds) if compounds else None,
    }


def generate_weekly_summary(stats):
    score = stats.get("weekly_score")
    score_text = f"{score:.0f}/100" if score is not None else "not available"
    mood = stats.get("most_common_mood") or "not enough mood data"
    emotion = stats.get("most_common_emotion") or "not enough emotion data"
    stress = f"{stats['avg_stress']:.1f}/10" if stats.get("avg_stress") is not None else "not available"
    sleep = f"{stats['avg_sleep']:.1f} hours" if stats.get("avg_sleep") is not None else "not available"
    compound = f"{stats['avg_compound']:.2f}" if stats.get("avg_compound") is not None else "not available"
    return (f"Your weekly wellness score is {score_text}, based on {stats['coverage_days']}/7 days ({stats['coverage_pct']:.2f}%) of actual stored wellness data. "
            f"Your most common mood was {mood}, and your most common detected emotion was {emotion}. "
            f"Average stress was {stress}, average sleep was {sleep}, and average compound sentiment was {compound}. "
            "Missing measurements were not treated as zero; only available components contributed to the score and their configured weights were redistributed.")


def recommendations(stats):
    rec = []
    if stats.get("avg_stress") is not None and stats["avg_stress"] >= 7:
        rec += ["Take regular short breaks during demanding periods.", "Prioritize urgent tasks and discuss sustained workload pressure when needed."]
    if stats.get("avg_sleep") is not None and stats["avg_sleep"] < 6:
        rec += ["Try to maintain a consistent sleep schedule and aim for sufficient nightly sleep."]
    if stats.get("high_workload_days", 0) >= 3:
        rec += ["Break large tasks into smaller steps and review workload distribution."]
    if stats.get("journal_consistency", 0) < 50:
        rec += ["Recording mood and wellness details more consistently will improve future weekly insights."]
    if not rec:
        rec = ["Continue the habits that are supporting your current wellness pattern.", "Maintain a healthy balance between focused work, recovery, sleep, and regular check-ins."]
    return rec


def achievements(stats):
    out = []
    if stats.get("coverage_days") == 7:
        out.append("🏆 7-Day Wellness Tracker")
    if stats.get("most_common_mood") in {"Amazing", "Happy"} or stats.get("positive_emotion_days", 0) > stats.get("negative_emotion_days", 0):
        out.append("😊 Positive Week")
    if stats.get("journal_days", 0) >= 5:
        out.append("💪 Consistent Journal Writer")
    if (stats.get("avg_stress") is not None and stats["avg_stress"] <= 4.5 and
        stats.get("avg_sleep") is not None and stats["avg_sleep"] >= 7 and
        stats.get("most_common_mood") in {"Amazing", "Happy", "Normal"}):
        out.append("🌟 Healthy Work-Life Balance")
    return out or ["🌱 Keep Building Your Wellness Record"]


def build_weekly_pdf(username, email, report, stats, summary, recs, awards, figures):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=32, leftMargin=32, topMargin=32, bottomMargin=32)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], alignment=TA_CENTER, fontSize=22, leading=27, spaceAfter=10))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontSize=14, leading=18, spaceBefore=10, spaceAfter=7))
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8.5, leading=11))
    story = [Paragraph("WEEKLY WELLNESS REPORT", styles["ReportTitle"]),
             Paragraph(f"Employee: {username} · {email}", styles["BodyText"]),
             Paragraph(f"Report Period: {report['start_date']} to {report['end_date']}", styles["BodyText"]), Spacer(1, 12)]
    score = f"{stats['weekly_score']:.0f} / 100" if stats.get("weekly_score") is not None else "Not available"
    overview = [
        ["Wellness Score", score], ["Data Coverage", f"{stats['coverage_days']} / 7 days ({stats['coverage_pct']:.2f}%)"],
        ["Journal Consistency", f"{stats['journal_days']} / 7 days ({stats['journal_consistency']:.2f}%)"],
        ["Average Stress", f"{stats['avg_stress']:.1f} / 10" if stats.get('avg_stress') is not None else "Unavailable"],
        ["Average Sleep", f"{stats['avg_sleep']:.1f} hrs" if stats.get('avg_sleep') is not None else "Unavailable"],
        ["Most Common Mood", stats.get("most_common_mood") or "Unavailable"],
        ["Most Common Emotion", stats.get("most_common_emotion") or "Unavailable"],
    ]
    t = Table(overview, colWidths=[2.2*inch, 3.8*inch])
    t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), colors.whitesmoke), ("GRID", (0,0), (-1,-1), .5, colors.lightgrey), ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"), ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("PADDING", (0,0), (-1,-1), 7)]))
    story += [t, Paragraph("AI Weekly Summary", styles["Section"]), Paragraph(summary, styles["BodyText"])]

    story.append(Paragraph("Daily Wellness Scores", styles["Section"]))
    rows = [["Date", "Mood", "Emotion", "Stress", "Sleep", "Workload", "Score"]]
    for d in report["days"]:
        rows.append([str(d["date"]), d.get("mood") or "—", d.get("emotion") or "—",
                     f"{d['stress_level']:.1f}" if d.get("stress_level") is not None else "—",
                     f"{d['sleep_hours']:.1f}" if d.get("sleep_hours") is not None else "—",
                     d.get("workload") or "—", f"{d['daily_score']:.1f}" if d.get("daily_score") is not None else "—"])
    dt = Table(rows, repeatRows=1, colWidths=[.75*inch, .75*inch, .85*inch, .55*inch, .55*inch, .7*inch, .55*inch])
    dt.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#6B21A8")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), .3, colors.lightgrey), ("FONTSIZE", (0,0), (-1,-1), 7), ("ALIGN", (0,0), (-1,-1), "CENTER"), ("VALIGN", (0,0), (-1,-1), "MIDDLE")]))
    story.append(dt)

    story.append(Paragraph("Analyses", styles["Section"]))
    analysis_lines = [
        f"Stress: average {stats['avg_stress']:.1f}/10, minimum {stats['min_stress']:.1f}, maximum {stats['max_stress']:.1f}, trend {stats['stress_trend'] or 'unavailable'}." if stats.get('avg_stress') is not None else "Stress: unavailable.",
        f"Sleep: average {stats['avg_sleep']:.1f} hours, minimum {stats['min_sleep']:.1f}, maximum {stats['max_sleep']:.1f}." if stats.get('avg_sleep') is not None else "Sleep: unavailable.",
        f"Workload: {stats.get('workload_counts') or 'unavailable'}; high-workload days: {stats.get('high_workload_days', 0)}.",
        f"Emotion confidence: {stats['avg_emotion_confidence']:.1%}." if stats.get('avg_emotion_confidence') is not None else "Emotion confidence: unavailable.",
        f"Sentiment averages: positive {stats['avg_positive']:.2f}, negative {stats['avg_negative']:.2f}, neutral {stats['avg_neutral']:.2f}, compound {stats['avg_compound']:.2f}." if stats.get('avg_positive') is not None else "Stored positive/negative/neutral sentiment scores are unavailable for this period; compound sentiment is used where stored.",
    ]
    for line in analysis_lines:
        story.append(Paragraph("• " + line, styles["BodyText"]))

    for title, fig in figures:
        if fig is None:
            continue
        img_buf = BytesIO()
        fig.savefig(img_buf, format="png", dpi=140, bbox_inches="tight")
        img_buf.seek(0)
        story += [Paragraph(title, styles["Section"]), Image(img_buf, width=6.1*inch, height=3.0*inch)]

    story.append(PageBreak())
    story.append(Paragraph("Personalized Recommendations", styles["Section"]))
    for r in recs:
        story.append(Paragraph("• " + r, styles["BodyText"]))
    story.append(Paragraph("Achievements", styles["Section"]))
    for a in awards:
        story.append(Paragraph(a, styles["BodyText"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("This report is based only on wellness information stored for the selected 7-day period. Missing values are shown as unavailable and are not treated as zero.", styles["Small"]))
    doc.build(story)
    return buf.getvalue()
