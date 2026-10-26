"""What to do next — fixed, checked steps. The model never invents these.

Every phone number and website here is a real, official one. Change them only
after checking the official source.
"""
from __future__ import annotations

PLAYBOOKS: dict[str, dict[str, list[str]]] = {
    "message": {
        "en": [
            "Don't click the link, call the number, or reply.",
            "If it says it's your bank or a company, call them using the number on the back of your card "
            "or on their real website — never the number in the message.",
            "Forward scam texts to 7726 (SPAM) so your phone carrier can block them, then delete.",
            "Report it at reportfraud.ftc.gov.",
        ],
        "ko": [
            "링크를 누르거나, 전화하거나, 답장하지 마세요.",
            "은행이나 회사라고 하면, 카드 뒷면이나 진짜 웹사이트에 있는 번호로 직접 전화하세요 — 문자 속 번호는 절대 안 됩니다.",
            "사기 문자는 7726(SPAM)으로 전달하면 통신사가 차단합니다. 그다음 삭제하세요.",
            "reportfraud.ftc.gov 에 신고하세요.",
        ],
    },
    "clicked": {
        "en": [
            "Call your bank now, using the number on the back of your card. Say you may have been scammed.",
            "Change your email password first, then your bank passwords. Turn on 2-step login.",
            "If you gave your Social Security number or ID, go to identitytheft.gov.",
            "Freeze your credit for free at Equifax, Experian and TransUnion.",
            "Report it at reportfraud.ftc.gov.",
        ],
        "ko": [
            "지금 카드 뒷면 번호로 은행에 전화해서 사기를 당했을 수 있다고 말하세요.",
            "이메일 비밀번호부터 바꾸고, 그다음 은행 비밀번호를 바꾸세요. 2단계 인증을 켜세요.",
            "사회보장번호(SSN)나 신분증 정보를 줬다면 identitytheft.gov 로 가세요.",
            "Equifax, Experian, TransUnion에서 신용을 무료로 동결하세요.",
            "reportfraud.ftc.gov 에 신고하세요.",
        ],
    },
    "fake_checks": {
        "en": [
            "Call your bank today. Report each check you didn't write as forged or counterfeit.",
            "Ask the bank for an 'affidavit of forgery' form for each check, and send it back quickly — "
            "banks have deadlines for reporting.",
            "Ask to close the account and open a new one with new numbers. Stop payment on any lost checks.",
            "If checks may have been stolen from your mail, report it at uspis.gov.",
            "File a police report and report it at reportfraud.ftc.gov.",
            "If the bank won't pay you back, file a complaint at consumerfinance.gov/complaint.",
        ],
        "ko": [
            "오늘 은행에 전화하세요. 직접 쓰지 않은 수표는 모두 위조라고 신고하세요.",
            "수표마다 '위조 진술서(affidavit of forgery)' 양식을 달라고 하고 빨리 보내세요 — 신고 기한이 있습니다.",
            "계좌를 닫고 새 번호로 새 계좌를 만들어 달라고 하세요. 잃어버린 수표는 지급 정지하세요.",
            "우편함에서 수표를 도난당했을 수 있으면 uspis.gov 에 신고하세요.",
            "경찰에 신고하고 reportfraud.ftc.gov 에도 신고하세요.",
            "은행이 돈을 돌려주지 않으면 consumerfinance.gov/complaint 에 민원을 넣으세요.",
        ],
    },
}


def steps(kind: str, lang: str = "en") -> list[str]:
    return PLAYBOOKS[kind]["ko" if lang == "ko" else "en"]
