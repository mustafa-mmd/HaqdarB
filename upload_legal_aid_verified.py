# upload_legal_aid_verified.py
from google.cloud import firestore
from google.oauth2 import service_account

CREDENTIALS_PATH = "haqdar-key.json"
credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
db = firestore.Client(credentials=credentials)

data = [
    # ── LAHORE ──
    {
        "city": "Lahore",
        "name": "AGHS Legal Aid Cell",
        "address": "131 E/1, Gulberg III, Lahore, Pakistan",
        "phone": "+92-42-5763234",
        "services": "Free legal aid, women's rights, children, bonded labourers, prisoners, human rights litigation"
    },
    {
        "city": "Lahore",
        "name": "Human Rights Commission of Pakistan (HRCP)",
        "address": "Aiwan-i-Jamhoor, 107 Tipu Block, New Garden Town, Lahore 54600",
        "phone": "+92-42-35864994",
        "services": "Human rights monitoring, legal aid, complaint handling, rights advocacy"
    },
    {
        "city": "Lahore",
        "name": "Punjab Commission on the Status of Women (PCSW)",
        "address": "Women Development Complex, G-Block Sabzazar, Lahore",
        "phone": "1043",
        "services": "Women's rights, legal advice, domestic violence complaints, referral services"
    },
    {
        "city": "Lahore",
        "name": "Digital Rights Foundation",
        "address": "Lahore, Pakistan",
        "phone": "0800-39393",
        "services": "Cyber harassment, online violence, digital security, legal guidance"
    },
    # ── KARACHI ──
    {
        "city": "Karachi",
        "name": "Legal Aid Society (LAS)",
        "address": "Block C, 1st Floor, FTC Building, Shahrah-e-Faisal, Karachi",
        "phone": "+92-21-35634112",
        "services": "Free legal advice, criminal defence, family law, women's rights, civil law"
    },
    {
        "city": "Karachi",
        "name": "Lawyers for Human Rights and Legal Aid (LHRLA)",
        "address": "D-1, Court View Apartment, Opposite Sindh Assembly, Court Road, Karachi",
        "phone": "+92-21-35674031",
        "services": "Human rights, legal aid, criminal defence, women's rights, child rights"
    },
    {
        "city": "Karachi",
        "name": "War Against Rape (WAR)",
        "address": "102 Pearl Crest, 18-C, Zamzama Boulevard, Phase V, DHA, Karachi",
        "phone": "+92-21-5373008",
        "services": "Sexual violence survivors, free legal aid, counselling, medical assistance"
    },
    # ── ISLAMABAD ──
    {
        "city": "Islamabad",
        "name": "Rozan",
        "address": "Adjacent Bahria Enclave, Pind Bhagwal Road, Islamabad 44000",
        "phone": "+92-51-2721900",
        "services": "Counselling, gender-based violence, mental health, legal guidance"
    },
    {
        "city": "Islamabad",
        "name": "Aurat Foundation",
        "address": "Office No.17, Second Floor, Zaki Centre, I-8 Markaz, Islamabad",
        "phone": "+92-51-2609596",
        "services": "Women's rights, legal awareness, advocacy, gender equality"
    },
    {
        "city": "Islamabad",
        "name": "SPARC",
        "address": "House #98, Street 05, MPCHS, E-11/1, Islamabad",
        "phone": "+92-51-2163011",
        "services": "Child rights, juvenile justice, child protection, child labour"
    },
    {
        "city": "Islamabad",
        "name": "National Commission for Human Rights (NCHR)",
        "address": "5th Floor, Evacuee Trust Complex, F-5, Islamabad",
        "phone": "1413",
        "services": "Human rights protection, complaints handling, legal support"
    },
    {
        "city": "Islamabad",
        "name": "Bedari",
        "address": "House #879, Street #79, I-8/3, Islamabad",
        "phone": "0300-5251717",
        "services": "Women's rights, free legal aid, psychological counselling"
    },
    # ── PESHAWAR ──
        {
        "city": "Peshawar",
        "name": "Human Rights Commission of Pakistan (HRCP) – Peshawar Office",
        "address": "43 Gulshan Iqbal Lane (near Arbab Road stop), University Road, Peshawar, Khyber‑Pakhtunkhwa",
        "phone": "0344 547 5553 (Gilgit mobile), +92-42-35864994 (Lahore secretariat)",
        "services": "Human rights monitoring, complaints cell for gender‑based violence, police excesses, minorities’ rights, forced marriage, cybercrime referrals"
    },
    {
        "city": "Peshawar",
        "name": "SHARP (Society for Human Rights & Prisoners’ Aid) – Peshawar",
        "address": "Peshawar, Khyber‑Pakhtunkhwa (SHARP established 1999, registered under Voluntary Social Welfare Agencies Ordinance 1961)",
        "phone": "0300-858 0417 (7am‑10pm, UNHCR legal assistance hotline)",
        "services": "Legal aid for refugees/asylum seekers, child protection, emergency response, advocacy, UNHCR partner (source: UNHCR help page)"
    },
    {
        "city": "Peshawar",
        "name": "Peshawar High Court – Helpline 1042",
        "address": "Peshawar High Court, Adjacent to KPK Provincial Assembly, Jail Road, Peshawar",
        "phone": "1042 (Toll‑free helpline, inaugurated by PHC Chief Justice)",
        "services": "Public access to court information, case updates in Pashto & Urdu (source: Express Tribune)"
    },
    {
        "city": "Peshawar",
        "name": "Madadgaar National Helpline (LHRLA) – Peshawar Contact Point",
        "address": "Karachi, Lahore, Peshawar & Quetta (nationwide coverage)",
        "phone": "1098 (Toll‑free), SMS: 0311-6641098",
        "services": "Child and women violence/abuse helpline, crisis intervention, legal aid, counselling (source: idoc.pub listing)"
    },
    {
        "city": "Peshawar",
        "name": "KP Lawyers for Rights Network (through Da Hawwa Lur)",
        "address": "Peshawar, Khyber‑Pakhtunkhwa (network launched December 2023)",
        "phone": "Contact via NCHR Peshawar provincial office or Ombudsperson KP",
        "services": "Free legal aid to women and transgender communities surviving gender‑based violence (source: The News)"
    },
    {
        "city": "Peshawar",
        "name": "Ministry of Human Rights (MoHR) – National Helpline 1099",
        "address": "Peshawar, Khyber‑Pakhtunkhwa (nationwide service, 24/7)",
        "phone": "1099 (Toll‑free), WhatsApp: 0333‑9085709",
        "services": "Free legal advice, human rights complaint intake, referral to authorities (source: Pakistan government press releases)"
    },
    {
        "city": "Peshawar",
        "name": "BOLO Helpline – Directorate of Social Welfare & Women Empowerment KP",
        "address": "Directorate General of Social Welfare, Peshawar, Khyber‑Pakhtunkhwa (provincial level)",
        "phone": "0800‑22227 (Toll‑free)",
        "services": "Gender‑based violence (GBV) victims, persons with disabilities, legal support, counselling (source: swkpk.gov.pk)"
    },
    {
        "city": "Peshawar",
        "name": "Justice Helpline International",
        "address": "Nationwide service, accessible from Peshawar",
        "phone": "+92-342-2005061",
        "services": "Free legal consultation, online legal advice, access to justice (source: justicehelpline.org)"
    },
    {
        "city": "Multan",
        "name": "LHC‑Approved Pro Bono Lawyers – Multan Bench",
        "address": "Multan Bench, Lahore High Court, Multan, Punjab",
        "phone": "Contact via Punjab Bar Council: +92‑42‑37360414",
        "services": "Free legal representation by approved lawyers: Muhammad Ali Butt, Muhammad Imran Saqi, Abdul Rahman Zauq, Muhammad Amir Imran Yousaf (source: Dunya News)"
    },
    {
        "city": "Multan",
        "name": "District Legal Empowerment Committee (DLEC) – Multan",
        "address": "Sessions Court, Multan, Punjab (DLEC present in every district of Pakistan)",
        "phone": "Contact via District & Sessions Judge, Multan, or Multan Bar Association",
        "services": "Free legal aid for deserving litigants, lawyer appointment, financial assistance up to Rs. 50,000. Nationwide, DLECs have assisted over 7,000 litigants (source: pjn.org.pk)"
    },
    {
        "city": "Multan",
        "name": "Human Rights Commission of Pakistan (HRCP) – Multan Regional Office",
        "address": "Multan, Punjab (regional office; complaints cell handles Multan cases, including referral to Women Help Desks and Violence against Women Centre)",
        "phone": "+92-42-35864994 (Lahore secretariat)",
        "services": "Human rights monitoring, legal aid, complaint handling, gender‑based violence referrals, referral to Multan shelters and police help desks (source: hrcp‑web.org Complaints Cell page)"
    },
    {
        "city": "Multan",
        "name": "Citizens Commission for Human Development (CCHD) – Multan Free Legal Aid Desks",
        "address": "Chambers of Advocates Athar Aziz and Maimoona Husnain, Multan, Punjab",
        "phone": "Contact via Multan Bar Association (Multan Bar President Sher Zaman Qureshi inaugurated the desks)",
        "services": "Free legal aid desks for the underprivileged under the Access to Justice and Supremacy of Law project (source: Express Tribune)"
    },
    {
        "city": "Multan",
        "name": "AGHS Legal Aid Cell – Multan Referral (via National Network)",
        "address": "No dedicated Multan office; serves Multan through nationwide network",
        "phone": "+92-42-35763599 (Lahore Head Office)",
        "services": "Free legal aid, women’s rights, child custody, domestic violence, bonded labour"
    },
    {
        "city": "Multan",
        "name": "Bedari – Crisis Helpline (operational in Multan area)",
        "address": "Bedari is a national‑level NGO; established a child helpline and crisis services in Multan area through the Girl Power Programme",
        "phone": "0300‑5251717 (Mon‑Fri 9am‑5pm)",
        "services": "Gender‑based violence, domestic abuse, child marriage, legal rights information, confidential counselling (source: IASP Find a Helpline)"
    },
    {
        "city": "Multan",
        "name": "Legal Aid Society (LAS) – Multan Outreach",
        "address": "Serves Multan via Karachi HQ; no fixed Multan office; users can also use the NAZ Assist chatbot for preliminary legal guidance",
        "phone": "+92-21-35634112, Toll‑free: 0800‑70806",
        "services": "Free legal advice (family law, criminal defence, property rights), SLACC helpline, NAZ Assist chatbot"
    },
    {
        "city": "Multan",
        "name": "Madadgaar National Helpline (LHRLA) – Multan Contact Point",
        "address": "Karachi, Lahore, Peshawar, Multan & Quetta (nationwide coverage)",
        "phone": "1098 (Toll‑free), SMS: 0311‑6641098",
        "services": "Child and women violence/abuse helpline, crisis intervention, legal aid, counselling"
    },
    {
        "city": "Multan",
        "name": "Ministry of Human Rights (MoHR) – National Helpline 1099",
        "address": "Nationwide service, accessible from Multan (24/7)",
        "phone": "1099 (Toll‑free), WhatsApp: 0333‑9085709",
        "services": "Free legal advice, human rights complaint intake, referral to authorities"
    },
    # ── NATIONWIDE ──
    {
        "city": "Pakistan-wide",
        "name": "Ministry of Human Rights Helpline",
        "address": "Government of Pakistan, Islamabad (nationwide)",
        "phone": "1099",
        "services": "Free legal advice, human rights complaints, women & child protection, 24/7"
    },
    {
        "city": "Pakistan-wide",
        "name": "Madadgaar National Helpline",
        "address": "Karachi, Pakistan (nationwide coverage)",
        "phone": "1098",
        "services": "Children violence/abuse, women violence/exploitation, crisis intervention, legal aid"
    },
    {
        "city": "Pakistan-wide",
        "name": "Justice Helpline International",
        "address": "Islamabad, Pakistan (nationwide service)",
        "phone": "+92-342-2005061",
        "services": "Free legal consultation, online legal advice, access to justice"
    },

    # ── QUETTA (Balochistan) ──
    {
        "city": "Quetta",
        "name": "National Commission for Human Rights (NCHR) – Balochistan Office",
        "address": "Office No 404/174-B, Lane 8, Jinnah Town, Quetta",
        "phone": "051-5595511",
        "services": "Human rights protection, complaint handling, legal support for human rights violations"
    },
    {
        "city": "Quetta",
        "name": "Balochistan Bar Council",
        "address": "Quetta High Court Building, Quetta, Balochistan",
        "phone": "+92-81-9202326",
        "services": "Lawyer regulation, bar association services, lawyer referral"
    },
    {
        "city": "Quetta",
        "name": "Taraqee Foundation",
        "address": "75-A, Chaman Housing Scheme, Airport Road, Quetta, Balochistan",
        "phone": "081-2864156",
        "services": "Access to justice, legal aid facilitation, poverty alleviation, social development, women empowerment"
    },
    {
        "city": "Quetta",
        "name": "Youth Association for Development (YAD)",
        "address": "E-26-Muslim Town, Officers Colony, Link Shabo Road, Tajjak Abad, Quetta",
        "phone": "+92-3342464598",
        "services": "Human rights, peace building, women empowerment, youth development, pro bono support"
    },
    {
        "city": "Quetta",
        "name": "Women Development Department (WDD) – Women Helpline 1089",
        "address": "Civil Secretariat, Quetta, Balochistan",
        "phone": "1089 (Toll‑free, 24/7)",
        "services": "Women harassment complaints, domestic violence, workplace harassment, property issues, legal support"
    },
    {
        "city": "Quetta",
        "name": "Legal Aid Society (LAS) – Balochistan Operations",
        "address": "Operations confirmed through Quetta Serena Hotel workshops; contact Karachi HQ for direct referrals",
        "phone": "+92-21-35634112 (Karachi Head Office), Toll‑free: 0800-70806",
        "services": "Free legal aid, SVR framework for violence survivors, criminal defence, legal helpline"
    },
    {
        "city": "Quetta",
        "name": "SHADE – Society for Human Advancement and Disadvantaged Empowerment",
        "address": "Registered in Balochistan; main office in Usta Muhammad, District Jaffarabad (serves Quetta referrals)",
        "phone": "Contact via NGO office (phone UNVERIFIED)",
        "services": "Free legal assistance for women, human rights education, advocacy, child victims of sexual abuse"
    },
    {
        "city": "Quetta",
        "name": "High Court of Balochistan – District Legal Empowerment Committee (DLEC)",
        "address": "Sessions Court, Zarghun Road, Quetta, Balochistan",
        "phone": "081-9201613, 081-9202323",
        "services": "Free legal aid for deserving litigants, lawyer appointment, financial assistance up to Rs. 50,000"
    },
    {
        "city": "Quetta",
        "name": "Manzil Organization Balochistan",
        "address": "House No. 333, Sumangli Housing Scheme, Sumangli Road, Quetta, Balochistan",
        "phone": "0346-8687813",
        "services": "Women‑led NGO, human rights, child protection, women empowerment, community development"
    },
    {
        "city": "Quetta",
        "name": "Society for Mobilization Advocacy And Justice (SMAAJ)",
        "address": "House No: 29–B, Chaman Housing Scheme, Airport Road, Quetta, Balochistan",
        "phone": "+92-300-8380350",
        "services": "Human rights, legal advocacy, justice promotion"
    },
    {
        "city": "Quetta",
        "name": "Rahnuma-Family Planning Association of Pakistan (FPAP) – Quetta",
        "address": "Family Health Hospital, Satellite Town, Block 4 Commercial Area, Quetta",
        "phone": "0800-44488 (Toll‑free Helpline)",
        "services": "Reproductive health, family planning, gender‑based violence support, women's health, legal guidance"
    },
    {
        "city": "Quetta",
        "name": "Balochistan Rural Support Programme (BRSP)",
        "address": "House No. 5-A, Gulshan-e-Janan Street, Saryab Road, Quetta, Balochistan",
        "phone": "081-2471437-39",
        "services": "Gender‑based violence support, community development, legal facilitation, women empowerment"
    },
    {
        "city": "Quetta",
        "name": "Justice Helpline International",
        "address": "Nationwide service, accessible from Balochistan",
        "phone": "+92-342-2005061",
        "services": "Free legal consultation, online legal advice, access to justice"
    },
]

for entry in data:
    doc_id = f"{entry['city']}_{entry['name']}".replace(" ", "_").replace(",", "")
    db.collection("legal_aid").document(doc_id).set(entry)
    print(f"Uploaded: {doc_id}")

print(f"✅ Total {len(data)} legal aid providers uploaded.")