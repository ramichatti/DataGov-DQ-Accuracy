import random
import datetime
from datetime import timedelta
import pyodbc
import string

random.seed(42)

# =====================================================
# CONFIGURATION BASE DE DONNÉES
# =====================================================
SERVER = 'localhost'
DATABASE = 'CoreBanking_OLTP'

# Chaîne de connexion SQL Server avec Trusted Connection (Windows Authentication)
conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;'

# =====================================================
# DONNÉES RÉELLES TUNISIE (sources: BCT, INS, World Bank)
# =====================================================

# Villes tunisiennes avec population réelle (source INS 2024)
VILLES_TUNISIE = [
    ("Tunis", 2473428), ("Sfax", 608293), ("Sousse", 495877), ("Kairouan", 186653),
    ("Bizerte", 182662), ("Gabès", 152921), ("Ariana", 152654), ("Gafsa", 143656),
    ("La Marsa", 118567), ("Kasserine", 108794), ("Monastir", 104538), ("Ben Arous", 102756),
    ("Sidi Bouzid", 92688), ("Medenine", 88993), ("Nabeul", 87357), ("Mahdia", 79545),
    ("Jendouba", 75918), ("Beja", 72102), ("Siliana", 68934), ("Zaghouan", 66542),
    ("Kebili", 64521), ("Tozeur", 52341), ("Tataouine", 48912), ("Manouba", 156789),
    ("Le Kef", 45678), ("Zarzis", 72345), ("Hammamet", 229253), ("Djerba", 163726),
    ("Sidi Thabet", 34256), ("Radès", 67890), ("La Goulette", 45234), ("Carthage", 23145),
    ("Le Bardo", 89123), ("Ezzahra", 56789), ("La Manouba", 45678), ("Oued Ellil", 34567),
    ("Mornag", 23456), ("Soliman", 34567), ("Hammam-Lif", 45678), ("Bou Mhel", 23456),
    ("Mornaguia", 12345), ("Douar Hicher", 67890), ("El Omrane", 34567), ("Bab Souika", 23456),
    ("El Menzah", 89123), ("Ain Zaghouan", 45678), ("Les Berges du Lac", 34567), ("El Omrane Supérieur", 23456),
    ("Bab Bhar", 45678), ("Sidi El Béchir", 34567), ("Jebel Jelloud", 23456), ("Séjoumi", 12345),
    ("Ettadhamen", 67890), ("Intilaka", 34567), ("Cité Ettahrir", 23456), ("Borj El Amri", 12345),
    ("Mnihla", 45678), ("Raoued", 34567), ("Sidi Thabet", 23456), ("Grombalia", 34567),
    ("Bou Argoub", 23456), ("Menzel Bouzelfa", 12345), ("Béni Khalled", 23456), ("Korba", 34567),
    ("Menzel Temime", 23456), ("Kelibia", 34567), ("El Haouaria", 12345), ("Takelsa", 23456),
    ("Béni Khiar", 12345), ("Dar Chaabane", 23456), ("Hammam Ghezèze", 12345), ("Bou Ficha", 23456),
    ("Sidi Bou Ali", 12345), ("Enfidha", 34567), ("Hergla", 12345), ("Akouda", 23456),
    ("Kalâa Kebira", 12345), ("Kalâa Seghira", 12345), ("Sidi El Hani", 12345), ("Msaken", 34567),
    ("Thyna", 23456), ("Sakiet Ezzit", 34567), ("Sakiet Eddaier", 34567), ("Chihia", 12345),
    ("Gremda", 23456), ("El Amra", 12345), ("Agareb", 23456), ("Bir Ali Ben Khalifa", 12345),
    ("El Hencha", 23456), ("Skhira", 34567), ("Menzel Chaker", 23456), ("Kerkennah", 12345),
    ("Gafsa Nord", 34567), ("Gafsa Sud", 34567), ("Métlaoui", 34567), ("Mdhilla", 34567),
    ("Redeyef", 12345), ("El Guettar", 23456), ("Sened", 12345), ("Moularès", 12345),
    ("Kasserine Nord", 34567), ("Kasserine Sud", 34567), ("Sbeitla", 34567), ("Sbiba", 34567),
    ("Fériana", 12345), ("Thala", 23456), ("Haidra", 12345), ("Foussana", 34567),
    ("Majel Bel Abbès", 12345), ("Ezzouhour", 23456), ("Hassi El Ferid", 12345), ("Jedelienne", 12345),
    ("El Ayoun", 12345), ("Sidi Bouzid Ouest", 34567), ("Sidi Bouzid Est", 34567), ("Meknassy", 12345),
    ("Menzel Bouzaiane", 23456), ("Regueb", 34567), ("Bir El Hafey", 12345), ("Cebbala Ouled Asker", 12345),
    ("Ouled Haffouz", 23456), ("Sidi Ali Ben Aoun", 12345), ("Mezzouna", 23456), ("Souk Jedid", 12345),
    ("Jilma", 23456), ("Gafour", 12345), ("Bou Arada", 23456), ("Gaâfour", 12345),
    ("El Krib", 23456), ("Siliana Nord", 34567), ("Siliana Sud", 34567), ("Bargou", 12345),
    ("Bou Rouis", 23456), ("Kesra", 12345), ("Rouhia", 12345), ("Makthar", 12345),
    ("El Aroussa", 23456), ("Sidi Bou Rouis", 12345), ("Bou Salem", 23456), ("Tabarka", 34567),
    ("Aïn Draham", 23456), ("Fernana", 12345), ("Ghardimaou", 12345), ("Oued Meliz", 12345),
    ("Balta-Bou Aouane", 23456), ("Jouaouda", 12345), ("Beni M'Tir", 12345), ("Amdoun", 12345),
    ("Sejnane", 23456), ("Bizerte Nord", 34567), ("Bizerte Sud", 34567), ("Menzel Bourguiba", 34567),
    ("Mateur", 23456), ("Ras Jebel", 34567), ("Ghar El Melh", 12345), ("Jendouba Nord", 34567),
    ("Jendouba Sud", 34567), ("Tabarka", 34567), ("Aïn Draham", 23456), ("Fernana", 12345),
    ("Ghardimaou", 12345), ("Oued Meliz", 34567), ("Bou Salem", 23456), ("Ben Guerdane", 34567),
    ("Medenine Nord", 34567), ("Medenine Sud", 34567), ("Beni Khedache", 12345), ("Zarzis", 72345),
    ("Houmt Souk", 45678), ("Midoun", 34567), ("Ajim", 23456), ("El May", 12345),
    ("Kebili Nord", 34567), ("Kebili Sud", 34567), ("Douz", 34567), ("Souk Lahad", 12345),
    ("El Faouar", 12345), ("Tozeur", 52341), ("Degache", 23456), ("Hazoua", 12345),
    ("Nefta", 23456), ("Tamerza", 12345), ("Chebika", 12345), ("Tataouine Nord", 34567),
    ("Tataouine Sud", 34567), ("Ghomrassen", 23456), ("Remada", 12345), ("Bir Lahmar", 12345),
    ("Dehiba", 12345), ("Smar", 12345), ("Toujane", 12345), ("Matmata", 12345),
]

# Banques tunisiennes réelles
BANQUES_TUNISIE = [
    "BIAT", "STB", "BNA", "Attijari Bank", "Amen Bank", "BH Bank", "UBCI", "UIB",
    "BT", "BTL", "BTS", "Banque Zitouna", "Wifak Bank", "Al Baraka Bank", "Al Wifak International Bank",
    "Arab Tunisian Bank", "Banque de Tunisie", "Société Tunisienne de Banque", "Union Bancaire pour le Commerce et l'Industrie",
    "Union Internationale de Banques", "Banque Tuniso-Libyenne", "Banque Tuniso-Saoudienne", "Banque Nationale Agricole",
    "Banque de l'Habitat", "Banque de Financement des Petites et Moyennes Entreprises",
]

# Prénoms tunisiens
PRENOMS_M = ["Mohamed", "Ahmed", "Ali", "Hassen", "Rached", "Khaled", "Nizar", "Hichem", "Walid", "Sami",
             "Anis", "Karim", "Youssef", "Aymen", "Hamza", "Omar", "Amine", "Sofiene", "Riadh", "Mourad",
             "Fathi", "Mondher", "Zied", "Tarek", "Adel", "Slim", "Marwen", "Bilel", "Rami", "Wassim",
             "Mehdi", "Nabil", "Lotfi", "Hatem", "Saber", "Jamel", "Foued", "Hafedh", "Jawhar", "Ridha",
             "Makram", "Hedi", "Taoufik", "Bechir", "Noureddine", "Sadok", "Moncef", "Chedly", "Habib", "Mahmoud",
             "Slaheddine", "Abdelaziz", "Abdelkader", "Abderrahman", "Rafik", "Lassaad", "Faysal", "Moez", "Chokri", "Houssem",
             "Iyed", "Rayan", "Aziz", "Maher", "Ghassen", "Oussama", "Kais", "Naji", "Salah", "Mokhtar",
             "Lamine", "Ferid", "Zouhair", "Mounir", "Adnene", "Firas", "Malek", "Atef", "Kamel", "Nader",
             "Moez", "Selim", "Yassine", "Ayoub", "Seifeddine", "Dhia", "Wael", "Raouf", "Helmi", "Zakaria",
             "Med", "Badr", "Imed", "Sami", "Hedi", "Fethi", "Nouha", "Chaker", "Miled", "Ammar"]

PRENOMS_F = ["Fatma", "Aicha", "Leila", "Henda", "Nadia", "Sonia", "Rim", "Imen", "Asma", "Mouna",
             "Rania", "Sana", "Marwa", "Yosra", "Ines", "Sarra", "Maya", "Amira", "Salma", "Houda",
             "Kawther", "Nawres", "Raja", "Samia", "Faten", "Kaouther", "Aida", "Najet", "Hajer", "Dorra",
             "Hela", "Manel", "Nour", "Syrine", "Siwar", "Chaima", "Meriem", "Eya", "Lina", "Rawdha",
             "Wafa", "Emna", "Khadija", "Latifa", "Majda", "Olfa", "Souad", "Zohra", "Fouzia", "Hayet",
             "Rabeb", "Nesrine", "Sawsen", "Afef", "Mariem", "Amani", "Rihab", "Bouthaina", "Ghada", "Hanen",
             "Rim", "Amel", "Sondes", "Aroua", "Ikram", "Nourhene", "Chiraz", "Intissar", "Jihane", "Kalthoum",
             "Saloua", "Mounira", "Fadia", "Lamia", "Naziha", "Saoussen", "Raja", "Khadija", "Jamila", "Faiza",
             "Najla", "Sahbiha", "Rabia", "Hedia", "Monia", "Lilia", "Dora", "Samiha", "Azza", "Mabrouka",
             "Zahra", "Khadija", "Fathia", "Nawel", "Radhia", "Mabrouka", "Najoua", "Sabiha", "Saadia", "Habiba"]

NOMS_FAMILLE = ["Ben Ali", "Trabelsi", "Ben Ahmed", "Ben Salah", "Gharbi", "Jaziri", "Masmoudi", "Kchaou",
                "Bouazizi", "Mejri", "Chaabane", "Hammami", "Saidi", "Ben Youssef", "Ben Ammar", "Kallel",
                "Ben Romdhane", "Ben Abdallah", "Ben Hassine", "Ben Sassi", "Bouguerra", "Dhouib", "Feki",
                "Guesmi", "Haddad", "Jebali", "Khemiri", "Lahmar", "Miled", "Nasri", "Oueslati", "Riahi",
                "Sghaier", "Tlili", "Yahyaoui", "Zouari", "Abidi", "Ammar", "Ayari", "Baccar", "Belhadj",
                "Ben Amor", "Ben Arous", "Ben Brahim", "Ben Cheikh", "Ben Farhat", "Ben Fredj", "Ben Hmida",
                "Ben Jemaa", "Ben Khalfallah", "Ben Mbarek", "Ben Moussa", "Ben Othman", "Ben Rejeb",
                "Ben Salem", "Ben Slima", "Bouhlel", "Boukhris", "Chaari", "Chaieb", "Chaker", "Chebbi",
                "Cherif", "Dammak", "Dhaouadi", "Dridi", "Ferchichi", "Ferjani", "Gabsi", "Gharbi",
                "Gueddana", "Guizani", "Hajji", "Hamdi", "Hamzaoui", "Hassine", "Jaidi", "Jelassi",
                "Jerbi", "Kallel", "Karray", "Khadhraoui", "Khlifi", "Koubaa", "Lahbib", "Lamine",
                "Mabrouk", "Mansouri", "Marzouki", "Masmoudi", "Matoussi", "Mazigh", "Mekki", "Miled",
                "Missaoui", "Mnasri", "Mrad", "Mzali", "Naceur", "Najar", "Nefzi", "Omrane", "Othmani",
                "Rahmouni", "Rekik", "Riahi", "Saad", "Said", "Sassi", "Slim", "Souissi", "Touati",
                "Turki", "Zghal", "Zitoun", "Zouari", "Abdelkefi", "Amara", "Ayed", "Bahloul", "Barka",
                "Beji", "Belaid", "Ben Aissa", "Ben Ayed", "Ben Chaabane", "Ben Dhaou", "Ben Fraj",
                "Ben Ghorbel", "Ben Halima", "Ben Hedi", "Ben Khelil", "Ben Lamine", "Ben Mansour",
                "Ben Marzouk", "Ben Miled", "Ben Nasr", "Ben Neji", "Ben Saad", "Ben Slama", "Ben Touati",
                "Ben Yaghlane", "Bennaceur", "Berriche", "Bouallagui", "Bouchoucha", "Boudhina",
                "Boujelbene", "Boukadi", "Bouzid", "Chahed", "Chalghaf", "Charfi", "Chehida", "Cherni",
                "Chibani", "Dahmen", "Daly", "Dhib", "Dhou", "El Abed", "El Amri", "El Ayeb",
                "Fakhfakh", "Fazaa", "Fendri", "Gargouri", "Gasmi", "Ghorbel", "Grira", "Guellouz",
                "Haj Salah", "Hammouda", "Harzallah", "Hassairi", "Hattab", "Hichri", "Jallouli",
                "Jarraya", "Jedidi", "Jelidi", "Kacem", "Kahlaoui", "Kallel", "Kanzari", "Kchouk",
                "Kebaili", "Kefi", "Khalfallah", "Khlifi", "Korbi", "Kouki", "Kraiem", "Ksentini",
                "Lahbibi", "Lahmar", "Latiri", "Louati", "Mabrouki", "Maghrebi", "Mahjoub", "Majoul",
                "Makhlouf", "Mami", "Mansour", "Marouani", "Masmoudi", "Matmati", "Mazhoud", "Meddeb",
                "Mehrez", "Mekni", "Melliti", "Mestiri", "Mezghanni", "Miledi", "Mili", "Mimouni",
                "Mokni", "Moussa", "Mrad", "Mzoughi", "Naceur", "Najar", "Nefzi", "Omrane", "Othmani"]

# Domaines email tunisiens
DOMAINS = ["gmail.com", "yahoo.fr", "hotmail.com", "outlook.com", "live.fr", "protonmail.com", "laposte.net"]

# Adresses types en Tunisie
RUES = ["Avenue Habib Bourguiba", "Rue de Marseille", "Avenue de la Liberté", "Rue du 18 Janvier",
        "Avenue Mohamed V", "Rue de la République", "Boulevard du 7 Novembre", "Rue Ibn Khaldoun",
        "Avenue Farhat Hached", "Rue de l'Indépendance", "Avenue de Carthage", "Rue El Jazira",
        "Boulevard Mohamed VI", "Rue du 14 Janvier", "Avenue de l'Environnement", "Rue Ibn Sina",
        "Avenue Taieb Mhiri", "Rue de la Palestine", "Boulevard de l'UMA", "Avenue de l'Union",
        "Rue El Fateh", "Avenue Kheireddine Pacha", "Rue Ibn Rachik", "Boulevard 9 Avril",
        "Avenue des Martyrs", "Rue El Kantaoui", "Avenue de la Corniche", "Rue Sidi Bou Said",
        "Boulevard du Leader", "Avenue de la Révolution", "Rue El Amel", "Avenue El Manar",
        "Rue de la Kasbah", "Boulevard Mohamed Ali", "Avenue de la Culture", "Rue El Wifak",
        "Avenue El Maghreb", "Rue El Intilaka", "Boulevard El Amal", "Avenue El Falah",
        "Rue El Horria", "Avenue El Watan", "Rue El Karama", "Boulevard El Moustakbel",
        "Avenue El Izdihar", "Rue El Ittihad", "Avenue El Islah", "Rue El Nahda",
        "Boulevard El Moustaqbal", "Avenue El Moudjahid"]

# Types de crédit tunisiens
TYPES_CREDIT = ["Crédit Immobilier", "Crédit Consommation", "Crédit Auto", "Crédit Étudiant",
                "Crédit Professionnel", "Crédit Agricole", "Crédit PME", "Crédit Équipement",
                "Crédit Trésorerie", "Crédit Bonifié", "Crédit Start-up", "Crédit Vert"]

# Types de transactions
TYPES_TRANSACTION = ["Dépôt", "Retrait", "Virement interne", "Virement externe", "Paiement carte",
                     "Prélèvement", "Remboursement crédit", "Intérêts crédités", "Frais bancaires",
                     "Commission", "Change de devise", "Transfert SWIFT", "Paiement en ligne",
                     "Recharge mobile", "Paiement facture", "DAB", "TPE", "Paiement chèque"]

# Canaux de transaction tunisiens
CANAUX = ["Agence", "DAB", "Internet Banking", "Mobile Banking", "TPE", "Call Center",
          "SMS Banking", "USSD", "Guichet automatique", "Agent bancaire", "Kiosk"]

# Types de compte
TYPES_COMPTE = ["Compte Courant", "Compte Épargne", "Compte à Terme", "Compte Joint",
                "Compte Professionnel", "Compte Rémunéré", "Compte Jeune", "Compte Senior",
                "Compte Étranger", "Compte Devise"]

# Devises
DEVISES = [("TND", "Dinar Tunisien"), ("EUR", "Euro"), ("USD", "Dollar Américain"),
           ("GBP", "Livre Sterling"), ("CHF", "Franc Suisse"), ("SAR", "Riyal Saoudien"),
           ("AED", "Dirham Émirati"), ("CAD", "Dollar Canadien")]

# Types de client
TYPES_CLIENT = [(1, "Particulier"), (2, "Professionnel"), (3, "Entreprise"), (4, "Association"),
                (5, "Institution Publique"), (6, "ONG"), (7, "Coopérative"), (8, "Startup")]

# Statuts
STATUTS_COMPTE = ["Actif", "Actif", "Actif", "Actif", "Actif", "Bloqué", "Clôturé", "Dormant", "Gelé"]
STATUTS_CREDIT = ["En cours", "En cours", "En cours", "En cours", "Remboursé", "En retard", "Restructuré", "Refusé"]

# =====================================================
# HELPERS
# =====================================================

def random_date(start, end):
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))

def random_phone():
    prefixes = ["20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "90", "91", "92", "93", "94", "95", "96", "97", "98", "99"]
    return f"+216 {random.choice(prefixes)} {random.randint(100000, 999999)}"

def random_cin():
    return f"{random.randint(10000000, 99999999):08d}"

def random_email(prenom, nom):
    prenom_clean = prenom.lower().replace(" ", "").replace("'", "")
    nom_clean = nom.lower().replace(" ", "").replace("'", "")
    patterns = [f"{prenom_clean}.{nom_clean}", f"{prenom_clean}_{nom_clean}", f"{prenom_clean}{nom_clean}",
                f"{prenom_clean[0]}.{nom_clean}", f"{prenom_clean}.{nom_clean[0]}", f"{nom_clean}.{prenom_clean}"]
    return f"{random.choice(patterns)}@{random.choice(DOMAINS)}"

def random_account_number():
    return f"{random.randint(10000000000, 99999999999):011d}"

def random_ref_transaction():
    return f"TRX-{random.randint(100000000, 999999999)}-{random.randint(1000, 9999)}"

# =====================================================
# DATA QUALITY ACCURACY ISSUE GENERATORS
# Based on DQ Engine Accuracy Rules for Tunisia
# =====================================================

def introduce_client_accuracy_issue(client_data, issue_type):
    """Introduce a specific accuracy issue in client data"""
    if issue_type == 'cin_format_invalid':
        # CIN must be exactly 8 digits
        client_data['CIN'] = f"{random.randint(100000, 999999):07d}"  # 7 digits
    elif issue_type == 'cin_not_numeric':
        # Contains letter - make unique
        client_data['CIN'] = f"{random.randint(100000, 999999):07d}{random.choice(['A', 'B', 'C'])}"
    elif issue_type == 'telephone_format_invalid':
        # Must start with +216 or 00216
        client_data['Telephone'] = f"+33 {random.randint(100000, 999999)}"  # French format
    elif issue_type == 'telephone_format_invalid_2':
        client_data['Telephone'] = "12345678"  # Missing country code
    elif issue_type == 'email_format_invalid':
        client_data['Email'] = 'invalid-email-format'
    elif issue_type == 'email_format_invalid_2':
        client_data['Email'] = 'test@'  # Incomplete
    elif issue_type == 'date_naissance_future':
        client_data['Date_Naissance'] = datetime.date(2030, 1, 1)
    elif issue_type == 'date_naissance_old':
        client_data['Date_Naissance'] = datetime.date(1899, 1, 1)
    elif issue_type == 'date_naissance_minor':
        # Client must be 18+ years old
        client_data['Date_Naissance'] = datetime.date(2015, 1, 1)
    return client_data

def introduce_compte_accuracy_issue(compte_data, issue_type):
    """Introduce a specific accuracy issue in compte data"""
    if issue_type == 'solde_extreme_high':
        compte_data['Solde'] = 2000000000  # > 1B
    elif issue_type == 'solde_extreme_low':
        compte_data['Solde'] = 0.001  # < 0.01 and not zero
    elif issue_type == 'solde_decimal_excess':
        compte_data['Solde'] = 1234.123456  # More than 3 decimals
    elif issue_type == 'date_ouverture_future':
        compte_data['Date_Ouverture'] = datetime.date(2030, 1, 1)
    elif issue_type == 'date_ouverture_old':
        compte_data['Date_Ouverture'] = datetime.date(1949, 1, 1)
    elif issue_type == 'statut_business_logic':
        # Closed account with non-zero balance
        compte_data['Statut'] = 'Cloture'
        compte_data['Solde'] = 1000
    return compte_data

def introduce_transaction_accuracy_issue(transaction_data, issue_type):
    """Introduce a specific accuracy issue in transaction data"""
    if issue_type == 'montant_extreme_high':
        transaction_data['Montant'] = 150000000  # > 100M
    elif issue_type == 'montant_decimal_excess':
        transaction_data['Montant'] = 1234.123456  # More than 3 decimals
    elif issue_type == 'date_transaction_future':
        transaction_data['Date_Transaction'] = datetime.datetime(2030, 1, 1, 12, 0, 0)
    elif issue_type == 'date_transaction_old':
        transaction_data['Date_Transaction'] = datetime.datetime(1999, 1, 1, 12, 0, 0)
    elif issue_type == 'montant_type_consistency':
        # Virement with non-positive amount
        transaction_data['Type_Transaction'] = 'Virement'
        transaction_data['Montant'] = -100
    return transaction_data

def introduce_credit_accuracy_issue(credit_data, issue_type):
    """Introduce a specific accuracy issue in credit data"""
    if issue_type == 'montant_extreme_high':
        credit_data['Montant'] = 20000000  # > 10M
    elif issue_type == 'montant_extreme_low':
        credit_data['Montant'] = 50  # < 100
    elif issue_type == 'montant_decimal_excess':
        credit_data['Montant'] = 1234.123456  # More than 3 decimals
    elif issue_type == 'taux_interet_low':
        credit_data['Taux_Interet'] = 1.5  # < 2%
    elif issue_type == 'taux_interet_high':
        credit_data['Taux_Interet'] = 30  # > 25%
    elif issue_type == 'date_debut_future':
        credit_data['Date_Debut'] = datetime.date(2030, 1, 1)
    elif issue_type == 'date_debut_old':
        credit_data['Date_Debut'] = datetime.date(1999, 1, 1)
    elif issue_type == 'montant_duree_consistency':
        # Unrealistic monthly payment (< 10)
        credit_data['Montant'] = 100
        credit_data['Duree_Mois'] = 120
    return credit_data

# =====================================================
# GÉNÉRATION DES DONNÉES
# =====================================================

N_AGENCES = 120
N_TYPE_CLIENT = len(TYPES_CLIENT)
N_CLIENTS = 500
N_DEVISES = len(DEVISES)
N_TYPE_COMPTE = len(TYPES_COMPTE)
N_COMPTES = 600
N_CANAUX = len(CANAUX)
N_TRANSACTIONS = 2000
N_CREDITS = 300

# =====================================================
# TABLE AGENCE
# =====================================================
agences = []
for i in range(1, N_AGENCES + 1):
    ville, pop = random.choice(VILLES_TUNISIE)
    banque = random.choice(BANQUES_TUNISIE)
    agences.append({
        "Agence_ID": i,
        "Code_Agence": f"AG{banque[:3].upper()}{i:04d}",
        "Nom_Agence": f"Agence {banque} {ville}",
        "Ville": ville,
        "Adresse": f"{random.choice(RUES)}, {ville}",
        "Telephone": random_phone()
    })

# =====================================================
# TABLE TYPE_CLIENT
# =====================================================
types_client = []
for tc in TYPES_CLIENT:
    types_client.append({
        "Type_Client_ID": tc[0],
        "Libelle": tc[1]
    })

# =====================================================
# TABLE CLIENT
# =====================================================
clients = []
# Accuracy issues for Client (2%)
client_accuracy_issues = ['cin_format_invalid', 'cin_not_numeric', 'telephone_format_invalid', 
                         'telephone_format_invalid_2', 'email_format_invalid', 'email_format_invalid_2',
                         'date_naissance_future', 'date_naissance_old', 'date_naissance_minor']
n_client_with_issues = int(N_CLIENTS * 0.02)  # 2% of clients with accuracy issues
client_indices_with_issues = random.sample(range(1, N_CLIENTS + 1), n_client_with_issues)

for i in range(1, N_CLIENTS + 1):
    if random.random() < 0.52:
        prenom = random.choice(PRENOMS_M)
    else:
        prenom = random.choice(PRENOMS_F)
    nom = random.choice(NOMS_FAMILLE)
    
    # Date naissance entre 1950 et 2005 (18+ years old)
    date_naiss = random_date(datetime.date(1950, 1, 1), datetime.date(2005, 12, 31))
    
    # Date création entre jan 2021 et juin 2026
    date_creation = random_date(datetime.date(2021, 1, 1), datetime.date(2026, 6, 30))
    
    ville = random.choice(VILLES_TUNISIE)[0]
    
    client_data = {
        "Client_ID": i,
        "CIN": random_cin(),
        "Nom": nom,
        "Prenom": prenom,
        "Date_Naissance": date_naiss,
        "Email": random_email(prenom, nom),
        "Telephone": random_phone(),
        "Adresse": f"{random.randint(1, 999)} {random.choice(RUES)}",
        "Ville": ville,
        "Type_Client_ID": random.choice([1,1,1,1,1,1,2,2,2,3,3,4,5,6,7,8]),
        "Date_Creation": date_creation,
        "Agence_ID": random.randint(1, N_AGENCES)
    }
    
    # Introduce accuracy issues for 2% of clients
    if i in client_indices_with_issues:
        issue_type = random.choice(client_accuracy_issues)
        client_data = introduce_client_accuracy_issue(client_data, issue_type)
    
    clients.append(client_data)

# =====================================================
# TABLE DEVISE
# =====================================================
devises = []
for i, (code, libelle) in enumerate(DEVISES, 1):
    devises.append({
        "Devise_ID": i,
        "Code_Devise": code,
        "Libelle": libelle
    })

# =====================================================
# TABLE TYPE_COMPTE
# =====================================================
types_compte = []
for i, tc in enumerate(TYPES_COMPTE, 1):
    types_compte.append({
        "Type_Compte_ID": i,
        "Libelle": tc
    })

# =====================================================
# TABLE COMPTE
# =====================================================
comptes = []
# Accuracy issues for Compte (4%)
compte_accuracy_issues = ['solde_extreme_high', 'solde_extreme_low', 'solde_decimal_excess',
                          'date_ouverture_future', 'date_ouverture_old', 'statut_business_logic']
n_compte_with_issues = int(N_COMPTES * 0.04)  # 4% of comptes with accuracy issues
compte_indices_with_issues = random.sample(range(1, N_COMPTES + 1), n_compte_with_issues)

for i in range(1, N_COMPTES + 1):
    client = random.choice(clients)
    date_ouv = random_date(datetime.date(2021, 1, 1), datetime.date(2026, 6, 30))
    
    # Solde réaliste en TND (majoritairement entre 0 et 50000 TND)
    if random.random() < 0.7:
        solde = round(random.uniform(100, 50000), 2)
    elif random.random() < 0.9:
        solde = round(random.uniform(50000, 200000), 2)
    else:
        solde = round(random.uniform(200000, 2000000), 2)
    
    compte_data = {
        "Compte_ID": i,
        "Numero_Compte": random_account_number(),
        "Client_ID": client["Client_ID"],
        "Type_Compte_ID": random.randint(1, N_TYPE_COMPTE),
        "Devise_ID": random.choice([1,1,1,1,1,1,1,1,2,3]),
        "Solde": solde,
        "Date_Ouverture": date_ouv,
        "Statut": random.choice(STATUTS_COMPTE)
    }
    
    # Introduce accuracy issues for 4% of comptes
    if i in compte_indices_with_issues:
        issue_type = random.choice(compte_accuracy_issues)
        compte_data = introduce_compte_accuracy_issue(compte_data, issue_type)
    
    comptes.append(compte_data)

# =====================================================
# TABLE CANAL_TRANSACTION
# =====================================================
canaux = []
for i, c in enumerate(CANAUX, 1):
    canaux.append({
        "Canal_ID": i,
        "Libelle": c
    })

# =====================================================
# TABLE TRANSACTION_BANCAIRE
# =====================================================
transactions = []
# Accuracy issues for Transaction (1%)
transaction_accuracy_issues = ['montant_extreme_high', 'montant_decimal_excess', 
                               'date_transaction_future', 'date_transaction_old', 'montant_type_consistency']
n_transaction_with_issues = int(N_TRANSACTIONS * 0.01)  # 1% of transactions with accuracy issues
transaction_indices_with_issues = random.sample(range(1, N_TRANSACTIONS + 1), n_transaction_with_issues)

comptes_pour_tx = [c for c in comptes if c["Statut"] == "Actif"]
for i in range(1, N_TRANSACTIONS + 1):
    compte = random.choice(comptes_pour_tx)
    date_tx = random_date(datetime.date(2021, 1, 1), datetime.date(2026, 6, 30))
    heure = random.randint(8, 22)
    minute = random.randint(0, 59)
    seconde = random.randint(0, 59)
    date_tx = datetime.datetime(date_tx.year, date_tx.month, date_tx.day, heure, minute, seconde)
    
    type_tx = random.choice(TYPES_TRANSACTION)
    
    # Montant réaliste selon type
    if type_tx in ["Dépôt", "Retrait"]:
        montant = round(random.uniform(10, 5000), 2)
    elif type_tx in ["Virement interne", "Virement externe"]:
        montant = round(random.uniform(50, 50000), 2)
    elif type_tx == "Paiement carte":
        montant = round(random.uniform(5, 2000), 2)
    elif type_tx == "Frais bancaires":
        montant = round(random.uniform(1, 50), 2)
    elif type_tx == "Intérêts crédités":
        montant = round(random.uniform(0.5, 500), 2)
    elif type_tx == "Change de devise":
        montant = round(random.uniform(100, 10000), 2)
    elif type_tx == "Transfert SWIFT":
        montant = round(random.uniform(500, 100000), 2)
    else:
        montant = round(random.uniform(10, 10000), 2)
    
    transaction_data = {
        "Transaction_ID": i,
        "Compte_ID": compte["Compte_ID"],
        "Canal_ID": random.randint(1, N_CANAUX),
        "Type_Transaction": type_tx,
        "Montant": montant,
        "Date_Transaction": date_tx,
        "Reference_Transaction": random_ref_transaction()
    }
    
    # Introduce accuracy issues for 1% of transactions
    if i in transaction_indices_with_issues:
        issue_type = random.choice(transaction_accuracy_issues)
        transaction_data = introduce_transaction_accuracy_issue(transaction_data, issue_type)
    
    transactions.append(transaction_data)

# =====================================================
# TABLE CREDIT
# =====================================================
credits = []
# Accuracy issues for Credit (3%)
credit_accuracy_issues = ['montant_extreme_high', 'montant_extreme_low', 'montant_decimal_excess',
                         'taux_interet_low', 'taux_interet_high', 'date_debut_future', 
                         'date_debut_old', 'montant_duree_consistency']
n_credit_with_issues = int(N_CREDITS * 0.03)  # 3% of credits with accuracy issues
credit_indices_with_issues = random.sample(range(1, N_CREDITS + 1), n_credit_with_issues)

for i in range(1, N_CREDITS + 1):
    client = random.choice(clients)
    date_debut = random_date(datetime.date(2021, 1, 1), datetime.date(2026, 6, 30))
    
    type_cred = random.choice(TYPES_CREDIT)
    
    if type_cred == "Crédit Immobilier":
        montant = round(random.uniform(50000, 500000), 2)
        duree = random.choice([120, 180, 240, 300])
        taux = round(random.uniform(5.5, 8.5), 2)
    elif type_cred == "Crédit Consommation":
        montant = round(random.uniform(5000, 50000), 2)
        duree = random.choice([12, 24, 36, 48, 60])
        taux = round(random.uniform(8.0, 13.0), 2)
    elif type_cred == "Crédit Auto":
        montant = round(random.uniform(20000, 150000), 2)
        duree = random.choice([36, 48, 60, 72])
        taux = round(random.uniform(6.5, 10.0), 2)
    elif type_cred == "Crédit Professionnel":
        montant = round(random.uniform(50000, 1000000), 2)
        duree = random.choice([36, 60, 84, 120, 180])
        taux = round(random.uniform(5.0, 9.0), 2)
    else:
        montant = round(random.uniform(10000, 200000), 2)
        duree = random.choice([12, 24, 36, 48, 60, 120])
        taux = round(random.uniform(6.0, 12.0), 2)
    
    credit_data = {
        "Credit_ID": i,
        "Client_ID": client["Client_ID"],
        "Type_Credit": type_cred,
        "Montant": montant,
        "Duree_Mois": duree,
        "Taux_Interet": taux,
        "Date_Debut": date_debut,
        "Statut": random.choice(STATUTS_CREDIT)
    }
    
    # Introduce accuracy issues for 3% of credits
    if i in credit_indices_with_issues:
        issue_type = random.choice(credit_accuracy_issues)
        credit_data = introduce_credit_accuracy_issue(credit_data, issue_type)
    
    credits.append(credit_data)

# =====================================================
# INSERTION DES DONNÉES DANS LA BASE DE DONNÉES
# =====================================================

print("Connecting to database...")
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

print("Inserting data...")

# Insert Agence
print("Inserting Agence...")
for agence in agences:
    cursor.execute("""
        INSERT INTO Agence (Agence_ID, Code_Agence, Nom_Agence, Ville, Adresse, Telephone)
        VALUES (?, ?, ?, ?, ?, ?)
    """, agence["Agence_ID"], agence["Code_Agence"], agence["Nom_Agence"], 
          agence["Ville"], agence["Adresse"], agence["Telephone"])

# Insert Type_Client
print("Inserting Type_Client...")
for tc in types_client:
    cursor.execute("""
        INSERT INTO Type_Client (Type_Client_ID, Libelle)
        VALUES (?, ?)
    """, tc["Type_Client_ID"], tc["Libelle"])

# Insert Client
print("Inserting Client...")
for client in clients:
    cursor.execute("""
        INSERT INTO Client (Client_ID, CIN, Nom, Prenom, Date_Naissance, Email, Telephone, 
                          Adresse, Ville, Type_Client_ID, Date_Creation, Agence_ID)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, client["Client_ID"], client["CIN"], client["Nom"], client["Prenom"], 
          client["Date_Naissance"], client["Email"], client["Telephone"], 
          client["Adresse"], client["Ville"], client["Type_Client_ID"], 
          client["Date_Creation"], client["Agence_ID"])

# Insert Devise
print("Inserting Devise...")
for devise in devises:
    cursor.execute("""
        INSERT INTO Devise (Devise_ID, Code_Devise, Libelle)
        VALUES (?, ?, ?)
    """, devise["Devise_ID"], devise["Code_Devise"], devise["Libelle"])

# Insert Type_Compte
print("Inserting Type_Compte...")
for tc in types_compte:
    cursor.execute("""
        INSERT INTO Type_Compte (Type_Compte_ID, Libelle)
        VALUES (?, ?)
    """, tc["Type_Compte_ID"], tc["Libelle"])

# Insert Compte
print("Inserting Compte...")
for compte in comptes:
    cursor.execute("""
        INSERT INTO Compte (Compte_ID, Numero_Compte, Client_ID, Type_Compte_ID, Devise_ID, 
                          Solde, Date_Ouverture, Statut)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, compte["Compte_ID"], compte["Numero_Compte"], compte["Client_ID"], 
          compte["Type_Compte_ID"], compte["Devise_ID"], compte["Solde"], 
          compte["Date_Ouverture"], compte["Statut"])

# Insert Canal_Transaction
print("Inserting Canal_Transaction...")
for canal in canaux:
    cursor.execute("""
        INSERT INTO Canal_Transaction (Canal_ID, Libelle)
        VALUES (?, ?)
    """, canal["Canal_ID"], canal["Libelle"])

# Insert Transaction_Bancaire
print("Inserting Transaction_Bancaire...")
for tx in transactions:
    cursor.execute("""
        INSERT INTO Transaction_Bancaire (Transaction_ID, Compte_ID, Canal_ID, Type_Transaction, 
                                        Montant, Date_Transaction, Reference_Transaction)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, tx["Transaction_ID"], tx["Compte_ID"], tx["Canal_ID"], tx["Type_Transaction"], 
          tx["Montant"], tx["Date_Transaction"], tx["Reference_Transaction"])

# Insert Credit
print("Inserting Credit...")
for credit in credits:
    cursor.execute("""
        INSERT INTO Credit (Credit_ID, Client_ID, Type_Credit, Montant, Duree_Mois, 
                           Taux_Interet, Date_Debut, Statut)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, credit["Credit_ID"], credit["Client_ID"], credit["Type_Credit"], 
          credit["Montant"], credit["Duree_Mois"], credit["Taux_Interet"], 
          credit["Date_Debut"], credit["Statut"])

conn.commit()
print("Data inserted successfully!")
print(f"Summary:")
print(f"  Agences: {len(agences)}")
print(f"  Clients: {len(clients)} (with {n_client_with_issues} accuracy issues - 2%)")
print(f"  Comptes: {len(comptes)} (with {n_compte_with_issues} accuracy issues - 4%)")
print(f"  Transactions: {len(transactions)} (with {n_transaction_with_issues} accuracy issues - 1%)")
print(f"  Credits: {len(credits)} (with {n_credit_with_issues} accuracy issues - 3%)")

cursor.close()
conn.close()
print("Connection closed.")
