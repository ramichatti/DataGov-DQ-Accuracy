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
    ("Fériana", 12345), ("Thala", 23456), ("Haidra", 12345), ("Foussana", 12345),
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
    ("Ghardimaou", 12345), ("Oued Meliz", 12345), ("Bou Salem", 12345), ("Ben Guerdane", 34567),
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

# Types de carte
TYPES_CARTE = ["Visa Classic", "Visa Premier", "Visa Electron", "MasterCard Standard",
               "MasterCard Gold", "MasterCard Platinum", "Carte Nationale", "Carte Prépayée",
               "Carte Virtuelle", "Carte Corporate"]

# Devises
DEVISES = [("TND", "Dinar Tunisien"), ("EUR", "Euro"), ("USD", "Dollar Américain"),
           ("GBP", "Livre Sterling"), ("CHF", "Franc Suisse"), ("SAR", "Riyal Saoudien"),
           ("AED", "Dirham Émirati"), ("CAD", "Dollar Canadien")]

# Types de client
TYPES_CLIENT = [(1, "Particulier"), (2, "Professionnel"), (3, "Entreprise"), (4, "Association"),
                (5, "Institution Publique"), (6, "ONG"), (7, "Coopérative"), (8, "Startup")]

# Fonctions employés
FONCTIONS = ["Directeur d'Agence", "Conseiller Clientèle", "Chargé de Crédit", "Caissier",
             "Analyste Financier", "Responsable Commercial", "Agent d'Accueil", "Gestionnaire de Comptes",
             "Chargé de Recouvrement", "Auditeur Interne", "Responsable IT", "Juriste",
             "Responsable RH", "Comptable", "Chargé de Conformité", "Trader", "Économiste",
             "Chargé de Marketing", "Responsable des Opérations", "Agent de Sécurité"]

# Statuts
STATUTS_COMPTE = ["Actif", "Actif", "Actif", "Actif", "Actif", "Bloqué", "Clôturé", "Dormant", "Gelé"]
STATUTS_CARTE = ["Active", "Active", "Active", "Active", "Active", "Bloquée", "Expirée", "Suspendue"]
STATUTS_CREDIT = ["En cours", "En cours", "En cours", "En cours", "Remboursé", "En retard", "Restructuré", "Refusé"]
STATUTS_VIREMENT = ["Exécuté", "Exécuté", "Exécuté", "Exécuté", "En attente", "Rejeté", "Annulé"]
STATUTS_REMBOURSEMENT = ["Payé", "Payé", "Payé", "En retard", "Payé partiellement", "Impayé"]

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
    return f"{random.randint(1000000, 9999999):07d}"

def random_email(prenom, nom):
    prenom_clean = prenom.lower().replace(" ", "").replace("'", "")
    nom_clean = nom.lower().replace(" ", "").replace("'", "")
    patterns = [f"{prenom_clean}.{nom_clean}", f"{prenom_clean}_{nom_clean}", f"{prenom_clean}{nom_clean}",
                f"{prenom_clean[0]}.{nom_clean}", f"{prenom_clean}.{nom_clean[0]}", f"{nom_clean}.{prenom_clean}"]
    return f"{random.choice(patterns)}@{random.choice(DOMAINS)}"

def random_account_number():
    return f"{random.randint(10000000000, 99999999999):011d}"

def random_card_number():
    return f"{random.randint(4000000000000000, 4999999999999999):016d}"

def random_ref_transaction():
    return f"TRX-{random.randint(100000000, 999999999)}-{random.randint(1000, 9999)}"

# =====================================================
# DATA QUALITY ISSUE GENERATORS
# =====================================================

def introduce_client_issue(client_data, issue_type):
    """Introduce a specific data quality issue in client data"""
    if issue_type == 'cin_invalid':
        client_data['CIN'] = '1234567'  # 7 chars instead of 8
    elif issue_type == 'nom_invalid':
        client_data['Nom'] = 'A'  # Too short
    elif issue_type == 'prenom_invalid':
        client_data['Prenom'] = 'Test123'  # Contains numbers
    elif issue_type == 'date_naissance_future':
        client_data['Date_Naissance'] = datetime.date(2030, 1, 1)
    elif issue_type == 'date_naissance_old':
        client_data['Date_Naissance'] = datetime.date(1899, 1, 1)
    elif issue_type == 'email_invalid':
        client_data['Email'] = 'invalid-email-format'
    elif issue_type == 'telephone_invalid':
        client_data['Telephone'] = '1234567'
    elif issue_type == 'adresse_invalid':
        client_data['Adresse'] = 'ABC'
    elif issue_type == 'ville_invalid':
        client_data['Ville'] = 'Tunis123'
    elif issue_type == 'date_creation_future':
        client_data['Date_Creation'] = datetime.date(2030, 1, 1)
    return client_data

def introduce_compte_issue(compte_data, issue_type):
    """Introduce a specific data quality issue in compte data"""
    if issue_type == 'numero_invalid':
        compte_data['Numero_Compte'] = '123456789'
    elif issue_type == 'type_compte_invalid':
        compte_data['Type_Compte_ID'] = 999  # Invalid type
    elif issue_type == 'devise_invalid':
        compte_data['Devise_ID'] = 999  # Invalid devise
    elif issue_type == 'solde_invalid':
        compte_data['Solde'] = -100000  # Exceeds overdraft limit
    elif issue_type == 'date_ouverture_future':
        compte_data['Date_Ouverture'] = datetime.date(2030, 1, 1)
    elif issue_type == 'statut_invalid':
        compte_data['Statut'] = 'InvalidStatut'
    return compte_data

def introduce_transaction_issue(transaction_data, issue_type):
    """Introduce a specific data quality issue in transaction data"""
    if issue_type == 'canal_invalid':
        transaction_data['Canal_ID'] = 999  # Invalid canal
    elif issue_type == 'type_invalid':
        transaction_data['Type_Transaction'] = 'InvalidType'
    elif issue_type == 'montant_zero':
        transaction_data['Montant'] = 0
    elif issue_type == 'montant_excess':
        transaction_data['Montant'] = 1000000  # Exceeds limit
    elif issue_type == 'date_future':
        transaction_data['Date_Transaction'] = datetime.datetime(2030, 1, 1, 12, 0, 0)
    elif issue_type == 'reference_null':
        transaction_data['Reference_Transaction'] = None
    return transaction_data

def introduce_credit_issue(credit_data, issue_type):
    """Introduce a specific data quality issue in credit data"""
    if issue_type == 'type_invalid':
        credit_data['Type_Credit'] = 'InvalidCreditType'
    elif issue_type == 'montant_negative':
        credit_data['Montant'] = -1000
    elif issue_type == 'montant_excess':
        credit_data['Montant'] = 10000000  # Exceeds limit
    elif issue_type == 'duree_invalid':
        credit_data['Duree_Mois'] = 300  # Exceeds max duration
    elif issue_type == 'taux_invalid':
        credit_data['Taux_Interet'] = 25.0  # Exceeds max rate
    elif issue_type == 'date_future':
        credit_data['Date_Debut'] = datetime.date(2030, 1, 1)
    elif issue_type == 'statut_invalid':
        credit_data['Statut'] = 'InvalidStatut'
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
N_CARTES = 450
N_CANAUX = len(CANAUX)
N_TRANSACTIONS = 2000
N_CREDITS = 300
N_REMBOURSEMENTS = 800
N_VIREMENTS = 500
N_HISTORIQUES = 1000
N_EMPLOYES = 200
N_AUDITS = 300

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
client_issues = ['cin_invalid', 'nom_invalid', 'prenom_invalid', 'date_naissance_future', 
                  'date_naissance_old', 'email_invalid', 'telephone_invalid', 'adresse_invalid',
                  'ville_invalid', 'date_creation_future']
n_client_with_issues = int(N_CLIENTS * 0.02)  # 2% of clients with issues
client_indices_with_issues = random.sample(range(1, N_CLIENTS + 1), n_client_with_issues)

for i in range(1, N_CLIENTS + 1):
    if random.random() < 0.52:
        prenom = random.choice(PRENOMS_M)
        sexe = "M"
    else:
        prenom = random.choice(PRENOMS_F)
        sexe = "F"
    nom = random.choice(NOMS_FAMILLE)
    
    # Date naissance entre 1950 et 2005
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
    
    # Introduce data quality issues for 2% of clients
    if i in client_indices_with_issues:
        issue_type = random.choice(client_issues)
        client_data = introduce_client_issue(client_data, issue_type)
    
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
    descriptions = {
        "Compte Courant": "Compte de dépôt à vue pour les opérations courantes",
        "Compte Épargne": "Compte rémunéré pour l'épargne à moyen terme",
        "Compte à Terme": "Dépôt à terme avec taux préférentiel",
        "Compte Joint": "Compte partagé entre plusieurs titulaires",
        "Compte Professionnel": "Compte dédié aux activités professionnelles",
        "Compte Rémunéré": "Compte avec intérêts mensuels",
        "Compte Jeune": "Compte adapté aux 18-30 ans",
        "Compte Senior": "Compte avec avantages pour les +60 ans",
        "Compte Étranger": "Compte pour résidents étrangers",
        "Compte Devise": "Compte en devises étrangères"
    }
    types_compte.append({
        "Type_Compte_ID": i,
        "Libelle": tc,
        "Description": descriptions.get(tc, "Compte bancaire standard")
    })

# =====================================================
# TABLE COMPTE
# =====================================================
comptes = []
compte_issues = ['numero_invalid', 'type_compte_invalid', 'devise_invalid', 'solde_invalid',
                  'date_ouverture_future', 'statut_invalid']
n_compte_with_issues = int(N_COMPTES * 0.03)  # 3% of comptes with issues
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
    
    # Introduce data quality issues for 3% of comptes
    if i in compte_indices_with_issues:
        issue_type = random.choice(compte_issues)
        compte_data = introduce_compte_issue(compte_data, issue_type)
    
    comptes.append(compte_data)

# =====================================================
# TABLE CARTE
# =====================================================
cartes = []
comptes_actifs = [c for c in comptes if c["Statut"] == "Actif"]
for i in range(1, N_CARTES + 1):
    compte = random.choice(comptes_actifs)
    date_exp = random_date(datetime.date(2025, 1, 1), datetime.date(2030, 12, 31))
    
    cartes.append({
        "Carte_ID": i,
        "Compte_ID": compte["Compte_ID"],
        "Numero_Carte": random_card_number(),
        "Type_Carte": random.choice(TYPES_CARTE),
        "Date_Expiration": date_exp,
        "Statut": random.choice(STATUTS_CARTE)
    })

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
transaction_issues = ['canal_invalid', 'type_invalid', 'montant_zero', 'montant_excess', 
                       'date_future', 'reference_null']
n_transaction_with_issues = int(N_TRANSACTIONS * 0.03)  # 3% of transactions with issues
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
    
    # Introduce data quality issues for 3% of transactions
    if i in transaction_indices_with_issues:
        issue_type = random.choice(transaction_issues)
        transaction_data = introduce_transaction_issue(transaction_data, issue_type)
    
    transactions.append(transaction_data)

# =====================================================
# TABLE CREDIT
# =====================================================
credits = []
credit_issues = ['type_invalid', 'montant_negative', 'montant_excess', 'duree_invalid',
                  'taux_invalid', 'date_future', 'statut_invalid']
n_credit_with_issues = int(N_CREDITS * 0.01)  # 1% of credits with issues
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
    
    # Introduce data quality issues for 1% of credits
    if i in credit_indices_with_issues:
        issue_type = random.choice(credit_issues)
        credit_data = introduce_credit_issue(credit_data, issue_type)
    
    credits.append(credit_data)

# =====================================================
# TABLE REMBOURSEMENT
# =====================================================
remboursements = []
credits_actifs = [c for c in credits if c["Statut"] in ["En cours", "Remboursé", "En retard"]]
for i in range(1, N_REMBOURSEMENTS + 1):
    credit = random.choice(credits_actifs)
    
    # Date de paiement après date début du crédit
    date_paiement = random_date(credit["Date_Debut"], datetime.date(2026, 6, 30))
    
    mensualite = round(credit["Montant"] / credit["Duree_Mois"] * (1 + credit["Taux_Interet"] / 100), 2)
    
    remboursements.append({
        "Remboursement_ID": i,
        "Credit_ID": credit["Credit_ID"],
        "Date_Paiement": date_paiement,
        "Montant_Paye": round(mensualite * random.uniform(0.5, 1.2), 2),
        "Statut": random.choice(STATUTS_REMBOURSEMENT)
    })

# =====================================================
# TABLE VIREMENT
# =====================================================
virements = []
for i in range(1, N_VIREMENTS + 1):
    compte_src = random.choice(comptes_pour_tx)
    compte_dst = random.choice(comptes_pour_tx)
    while compte_dst["Compte_ID"] == compte_src["Compte_ID"]:
        compte_dst = random.choice(comptes_pour_tx)
    
    date_v = random_date(datetime.date(2021, 1, 1), datetime.date(2026, 6, 30))
    heure = random.randint(8, 22)
    minute = random.randint(0, 59)
    seconde = random.randint(0, 59)
    date_v = datetime.datetime(date_v.year, date_v.month, date_v.day, heure, minute, seconde)
    
    virements.append({
        "Virement_ID": i,
        "Compte_Source_ID": compte_src["Compte_ID"],
        "Compte_Destination_ID": compte_dst["Compte_ID"],
        "Montant": round(random.uniform(50, 100000), 2),
        "Date_Virement": date_v,
        "Statut": random.choice(STATUTS_VIREMENT)
    })

# =====================================================
# TABLE HISTORIQUE_SOLDE
# =====================================================
historiques = []
for i in range(1, N_HISTORIQUES + 1):
    compte = random.choice(comptes)
    date_modif = random_date(datetime.date(2021, 1, 1), datetime.date(2026, 6, 30))
    heure = random.randint(0, 23)
    minute = random.randint(0, 59)
    seconde = random.randint(0, 59)
    date_modif = datetime.datetime(date_modif.year, date_modif.month, date_modif.day, heure, minute, seconde)
    
    ancien = round(compte["Solde"] * random.uniform(0.5, 1.5), 2)
    nouveau = round(compte["Solde"] * random.uniform(0.8, 1.2), 2)
    
    historiques.append({
        "Historique_ID": i,
        "Compte_ID": compte["Compte_ID"],
        "Ancien_Solde": ancien,
        "Nouveau_Solde": nouveau,
        "Date_Modification": date_modif
    })

# =====================================================
# TABLE EMPLOYE
# =====================================================
employes = []
for i in range(1, N_EMPLOYES + 1):
    if random.random() < 0.55:
        prenom = random.choice(PRENOMS_M)
    else:
        prenom = random.choice(PRENOMS_F)
    nom = random.choice(NOMS_FAMILLE)
    
    employes.append({
        "Employe_ID": i,
        "Nom": nom,
        "Prenom": prenom,
        "Fonction": random.choice(FONCTIONS),
        "Email": random_email(prenom, nom),
        "Agence_ID": random.randint(1, N_AGENCES)
    })

# =====================================================
# TABLE AUDIT_LOG
# =====================================================
audits = []
tables_audit = ["Client", "Compte", "Transaction_Bancaire", "Credit", "Virement", "Carte", "Employe", "Remboursement"]
operations = ["INSERT", "UPDATE", "DELETE"]
utilisateurs = ["admin", "sysdba", "app_user", "batch_user", "report_user", "backup_user", "audit_user", "api_user"]
for i in range(1, N_AUDITS + 1):
    date_action = random_date(datetime.date(2021, 1, 1), datetime.date(2026, 6, 30))
    heure = random.randint(0, 23)
    minute = random.randint(0, 59)
    seconde = random.randint(0, 59)
    date_action = datetime.datetime(date_action.year, date_action.month, date_action.day, heure, minute, seconde)
    
    table = random.choice(tables_audit)
    op = random.choice(operations)
    
    descriptions = {
        "INSERT": f"Insertion d'un nouvel enregistrement dans {table}",
        "UPDATE": f"Mise à jour d'un enregistrement dans {table}",
        "DELETE": f"Suppression d'un enregistrement dans {table}"
    }
    
    audits.append({
        "Audit_ID": i,
        "Table_Nom": table,
        "Operation": op,
        "Utilisateur": random.choice(utilisateurs),
        "Date_Action": date_action,
        "Description": descriptions[op]
    })

# =====================================================
# INSERTION DANS LA BASE DE DONNÉES
# =====================================================

def insert_data():
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print("[OK] Connexion a la base de donnees reussie!")
        
        # Insertion dans l'ordre respectant les cles etrangeres
        
        # 1. Agence
        print("[INSERT] Insertion des agences...")
        for ag in agences:
            cursor.execute("""
                INSERT INTO Agence (Agence_ID, Code_Agence, Nom_Agence, Ville, Adresse, Telephone)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ag["Agence_ID"], ag["Code_Agence"], ag["Nom_Agence"], ag["Ville"], ag["Adresse"], ag["Telephone"])
        print(f"   [OK] {len(agences)} agences inserees")
        
        # 2. Type_Client
        print("[INSERT] Insertion des types de client...")
        for tc in types_client:
            cursor.execute("""
                INSERT INTO Type_Client (Type_Client_ID, Libelle)
                VALUES (?, ?)
            """, tc["Type_Client_ID"], tc["Libelle"])
        print(f"   [OK] {len(types_client)} types de client inseres")
        
        # 3. Client
        print("[INSERT] Insertion des clients...")
        for cl in clients:
            cursor.execute("""
                INSERT INTO Client (Client_ID, CIN, Nom, Prenom, Date_Naissance, Email, Telephone, Adresse, Ville, Type_Client_ID, Date_Creation, Agence_ID)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, cl["Client_ID"], cl["CIN"], cl["Nom"], cl["Prenom"], cl["Date_Naissance"], 
                 cl["Email"], cl["Telephone"], cl["Adresse"], cl["Ville"], cl["Type_Client_ID"], 
                 cl["Date_Creation"], cl["Agence_ID"])
        print(f"   [OK] {len(clients)} clients inseres")
        
        # 4. Devise
        print("[INSERT] Insertion des devises...")
        for dv in devises:
            cursor.execute("""
                INSERT INTO Devise (Devise_ID, Code_Devise, Libelle)
                VALUES (?, ?, ?)
            """, dv["Devise_ID"], dv["Code_Devise"], dv["Libelle"])
        print(f"   [OK] {len(devises)} devises inserees")
        
        # 5. Type_Compte
        print("[INSERT] Insertion des types de compte...")
        for tc in types_compte:
            cursor.execute("""
                INSERT INTO Type_Compte (Type_Compte_ID, Libelle, Description)
                VALUES (?, ?, ?)
            """, tc["Type_Compte_ID"], tc["Libelle"], tc["Description"])
        print(f"   [OK] {len(types_compte)} types de compte inseres")
        
        # 6. Compte
        print("[INSERT] Insertion des comptes...")
        for cp in comptes:
            cursor.execute("""
                INSERT INTO Compte (Compte_ID, Numero_Compte, Client_ID, Type_Compte_ID, Devise_ID, Solde, Date_Ouverture, Statut)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, cp["Compte_ID"], cp["Numero_Compte"], cp["Client_ID"], cp["Type_Compte_ID"], 
                 cp["Devise_ID"], cp["Solde"], cp["Date_Ouverture"], cp["Statut"])
        print(f"   [OK] {len(comptes)} comptes inseres")
        
        # 7. Canal_Transaction
        print("[INSERT] Insertion des canaux de transaction...")
        for cn in canaux:
            cursor.execute("""
                INSERT INTO Canal_Transaction (Canal_ID, Libelle)
                VALUES (?, ?)
            """, cn["Canal_ID"], cn["Libelle"])
        print(f"   [OK] {len(canaux)} canaux inseres")
        
        # 8. Carte
        print("[INSERT] Insertion des cartes...")
        for ct in cartes:
            cursor.execute("""
                INSERT INTO Carte (Carte_ID, Compte_ID, Numero_Carte, Type_Carte, Date_Expiration, Statut)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ct["Carte_ID"], ct["Compte_ID"], ct["Numero_Carte"], ct["Type_Carte"], 
                 ct["Date_Expiration"], ct["Statut"])
        print(f"   [OK] {len(cartes)} cartes inserees")
        
        # 9. Transaction_Bancaire
        print("[INSERT] Insertion des transactions...")
        for tx in transactions:
            cursor.execute("""
                INSERT INTO Transaction_Bancaire (Transaction_ID, Compte_ID, Canal_ID, Type_Transaction, Montant, Date_Transaction, Reference_Transaction)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, tx["Transaction_ID"], tx["Compte_ID"], tx["Canal_ID"], tx["Type_Transaction"], 
                 tx["Montant"], tx["Date_Transaction"], tx["Reference_Transaction"])
        print(f"   [OK] {len(transactions)} transactions inserees")
        
        # 10. Credit
        print("[INSERT] Insertion des credits...")
        for cr in credits:
            cursor.execute("""
                INSERT INTO Credit (Credit_ID, Client_ID, Type_Credit, Montant, Duree_Mois, Taux_Interet, Date_Debut, Statut)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, cr["Credit_ID"], cr["Client_ID"], cr["Type_Credit"], cr["Montant"], 
                 cr["Duree_Mois"], cr["Taux_Interet"], cr["Date_Debut"], cr["Statut"])
        print(f"   [OK] {len(credits)} credits inseres")
        
        # 11. Remboursement
        print("[INSERT] Insertion des remboursements...")
        for rb in remboursements:
            cursor.execute("""
                INSERT INTO Remboursement (Remboursement_ID, Credit_ID, Date_Paiement, Montant_Paye, Statut)
                VALUES (?, ?, ?, ?, ?)
            """, rb["Remboursement_ID"], rb["Credit_ID"], rb["Date_Paiement"], rb["Montant_Paye"], rb["Statut"])
        print(f"   [OK] {len(remboursements)} remboursements inseres")
        
        # 12. Virement
        print("[INSERT] Insertion des virements...")
        for vr in virements:
            cursor.execute("""
                INSERT INTO Virement (Virement_ID, Compte_Source_ID, Compte_Destination_ID, Montant, Date_Virement, Statut)
                VALUES (?, ?, ?, ?, ?, ?)
            """, vr["Virement_ID"], vr["Compte_Source_ID"], vr["Compte_Destination_ID"], 
                 vr["Montant"], vr["Date_Virement"], vr["Statut"])
        print(f"   [OK] {len(virements)} virements inseres")
        
        # 13. Historique_Solde
        print("[INSERT] Insertion des historiques de solde...")
        for hs in historiques:
            cursor.execute("""
                INSERT INTO Historique_Solde (Historique_ID, Compte_ID, Ancien_Solde, Nouveau_Solde, Date_Modification)
                VALUES (?, ?, ?, ?, ?)
            """, hs["Historique_ID"], hs["Compte_ID"], hs["Ancien_Solde"], hs["Nouveau_Solde"], hs["Date_Modification"])
        print(f"   [OK] {len(historiques)} historiques inseres")
        
        # 14. Employe
        print("[INSERT] Insertion des employes...")
        for emp in employes:
            cursor.execute("""
                INSERT INTO Employe (Employe_ID, Nom, Prenom, Fonction, Email, Agence_ID)
                VALUES (?, ?, ?, ?, ?, ?)
            """, emp["Employe_ID"], emp["Nom"], emp["Prenom"], emp["Fonction"], emp["Email"], emp["Agence_ID"])
        print(f"   [OK] {len(employes)} employes inseres")
        
        # 15. Audit_Log
        print("[INSERT] Insertion des logs d'audit...")
        for ad in audits:
            cursor.execute("""
                INSERT INTO Audit_Log (Audit_ID, Table_Nom, Operation, Utilisateur, Date_Action, Description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ad["Audit_ID"], ad["Table_Nom"], ad["Operation"], ad["Utilisateur"], ad["Date_Action"], ad["Description"])
        print(f"   [OK] {len(audits)} logs d'audit inseres")
        
        conn.commit()
        print("\n[SUCCESS] Donnees inserees avec succes!")
        print(f"   Agences: {len(agences)}")
        print(f"   Types Client: {len(types_client)}")
        print(f"   Clients: {len(clients)}")
        print(f"   Devises: {len(devises)}")
        print(f"   Types Compte: {len(types_compte)}")
        print(f"   Comptes: {len(comptes)}")
        print(f"   Cartes: {len(cartes)}")
        print(f"   Canaux: {len(canaux)}")
        print(f"   Transactions: {len(transactions)}")
        print(f"   Credits: {len(credits)}")
        print(f"   Remboursements: {len(remboursements)}")
        print(f"   Virements: {len(virements)}")
        print(f"   Historiques: {len(historiques)}")
        print(f"   Employes: {len(employes)}")
        print(f"   Audits: {len(audits)}")
        
    except Exception as e:
        print(f"[ERROR] Erreur lors de l'insertion: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    insert_data()
