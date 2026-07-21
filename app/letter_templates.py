"""Launch letter templates (plan §6).

Register rule: these are formal, lawful petitions to a Union Minister —
respectful in address, firm in demand, no satire, no abuse, no personal
attacks. Paragraphs are separated by blank lines. The PDF layer adds the
sender line, date, ministry address, subject, salutation and signature
block around this body text.
"""
from .extensions import db
from .models import LetterTemplate

TEMPLATES = [
    {
        "slug": "neet-accountability",
        "title": "T1 — NEET-UG leak: accountability & exam-integrity reform",
        "subject_line": (
            "Accountability for the NEET-UG 2026 paper leak and urgent reform "
            "of examination integrity"
        ),
        "body": """\
I write to you as a citizen of India, deeply troubled by the confirmed leak of the NEET-UG 2026 question paper and the cancellation of the examination that followed. Lakhs of students prepared for this examination over years, at great personal and financial cost to their families. Its cancellation — made necessary by a failure of the examination system itself — has placed their futures in painful uncertainty through no fault of their own.

A confirmed paper leak is not a clerical lapse. It is a failure of custodianship over a process on which millions of young Indians stake their futures. When an examination of this scale can be compromised, every rank, every admission and every year of honest preparation is called into question. Public confidence in our national examinations, once lost, is not easily restored.

I therefore respectfully urge the Ministry to act on the following: first, announce a clear and binding timeline for the conduct of the re-examination, so that students can plan their lives with certainty; second, institute genuinely independent oversight of the National Testing Agency and the conduct of national entrance examinations, with its findings placed in the public domain; third, fix responsibility for the leak publicly and at every level at which the failure occurred, so that accountability is seen to be done; and fourth, ensure that students affected by the cancellation — many of whom have exhausted attempts, age limits or family savings — are treated with fairness and compassion in whatever remedial arrangements are made.

The young people affected by this failure have done everything our system asked of them. They studied, they qualified, they appeared. The system did not keep its side of the bargain. I ask you, as the Minister responsible, to ensure that it now does — visibly, verifiably and without delay.

I request that this letter be placed on record and that the Ministry's response be communicated in due course.""",
    },
    {
        "slug": "solidarity-humane-treatment",
        "title": "T2 — Solidarity with protesting students; humane treatment",
        "subject_line": (
            "Humane treatment of peaceful protesters and good-faith dialogue "
            "with students at Jantar Mantar"
        ),
        "body": """\
I write to you as a citizen of India regarding the students and young people who have been gathered in peaceful protest at Jantar Mantar since 20 June 2026, seeking accountability for the NEET-UG 2026 paper leak and reform of our examination system.

As has been widely reported, Shri Sonam Wangchuk was hospitalised on 18 July after an extended hunger strike undertaken in support of the students' demands. On 20 July, a march towards Parliament was met with tear gas and lathi charge, and a large number of young people were reported injured. Whatever one's view of the protesters' demands, these are our own citizens — students, graduates and young job-seekers — exercising the right to peaceful assembly that the Constitution of India guarantees them under Article 19.

I therefore respectfully urge the following: first, that the Government engage in structured, good-faith dialogue with the protesting students and their representatives, building on the outreach initiated on 20 July, so that their grievances are heard through discussion rather than confrontation; second, that all authorities concerned exercise the utmost restraint in the policing of peaceful assemblies, and that any use of force be strictly proportionate and independently reviewed; third, that protesters on hunger strike receive prompt and adequate medical care, administered with dignity; and fourth, that no student or young person face reprisal, academic or otherwise, for having participated peacefully in these protests.

The anger of these young people did not arise from nothing. It arose from a compromised examination and from the sense that no one has answered for it. Meeting that anger with force will not resolve it; meeting it with accountability may. I ask you to be the Minister who chose dialogue.

I request that this letter be placed on record and that the Ministry's response be communicated in due course.""",
    },
    {
        "slug": "cost-to-families",
        "title": "T3 — A citizen's letter: what a broken exam costs a family",
        "subject_line": (
            "What the failure of examination integrity costs ordinary Indian "
            "families"
        ),
        "body": """\
I write to you as an ordinary citizen, to place before you what the failure of an examination actually costs a family — because in the language of committees and inquiries, this cost is easily lost.

When a child in an ordinary Indian household prepares for a national entrance examination, the whole family prepares with them. Parents take loans for coaching fees that can run into lakhs of rupees. Families relocate to coaching towns, paying rents they can barely afford. Siblings adjust their own ambitions. For two years or more, every household decision bends around one examination date. This is done willingly, because families believe the examination is fair — that effort, not access, decides the outcome.

The confirmed leak of the NEET-UG 2026 question paper, and the cancellation that followed, broke that belief. The savings are spent either way. The years are spent either way. But now the family must find the money, the time and the strength to do it all again — because someone entrusted with the integrity of the examination failed, and because those who bought the paper thought they could buy a future that other children were earning.

I respectfully urge the Ministry to recognise that examination integrity is not an administrative matter but a promise made to families, and to act accordingly: publish a firm timeline for the re-examination; ensure the re-examination is conducted under demonstrably tightened security with independent oversight; fix responsibility for the leak publicly; and consider practical relief — in fees, attempts and age relaxation — for the students forced to appear twice for one examination.

Ordinary families do not ask for much from the examination system. They ask only that it not be for sale. I ask you to make that true again, and to be seen making it true.

I request that this letter be placed on record and that the Ministry's response be communicated in due course.""",
    },
]


def seed_templates():
    """Idempotent: inserts missing templates, leaves existing rows untouched."""
    for t in TEMPLATES:
        if not LetterTemplate.query.filter_by(slug=t["slug"]).first():
            db.session.add(LetterTemplate(**t))
    db.session.commit()
