CREATE DATABASE CoreBanking_DW;
GO

USE CoreBanking_DW;
GO


/* =====================================================
   DIMENSION AGENCE
   Source : OLTP.Agence
===================================================== */

CREATE TABLE Dim_Agence
(
    Agence_Key    INT IDENTITY(1,1) PRIMARY KEY,

    Code_Agence   VARCHAR(20) NOT NULL,
    Nom_Agence    VARCHAR(100),
    Ville         VARCHAR(50),
    Adresse       VARCHAR(200),
    Telephone     VARCHAR(20)
);
GO


/* =====================================================
   DIMENSION CLIENT
   Source : OLTP.Client + Type_Client
===================================================== */

CREATE TABLE Dim_Client
(
    Client_Key       INT IDENTITY(1,1) PRIMARY KEY,

    CIN              VARCHAR(8),
    Nom              VARCHAR(50),
    Prenom           VARCHAR(50),

    Date_Naissance   DATE,

    Email            VARCHAR(100),
    Telephone        VARCHAR(20),

    Adresse          VARCHAR(200),
    Ville            VARCHAR(50),

    Type_Client      VARCHAR(50),

    Date_Creation    DATE
);
GO


/* =====================================================
   DIMENSION COMPTE
   Source : OLTP.Compte + Type_Compte + Devise
===================================================== */

CREATE TABLE Dim_Compte
(
    Compte_Key       INT IDENTITY(1,1) PRIMARY KEY,

    Numero_Compte    VARCHAR(30),
    Type_Compte      VARCHAR(50),

    Devise           VARCHAR(50),

    Solde            DECIMAL(15,2),

    Date_Ouverture   DATE,

    Statut           VARCHAR(20)
);
GO


/* =====================================================
   DIMENSION TRANSACTION
   Source : OLTP.Transaction_Bancaire
            + Canal_Transaction
===================================================== */

CREATE TABLE Dim_Transaction
(
    Transaction_Key  BIGINT IDENTITY(1,1) PRIMARY KEY,

    Canal            VARCHAR(50),

    Type_Transaction VARCHAR(50),

    Montant          DECIMAL(15,2),

    Date_Transaction DATETIME,

    Reference        VARCHAR(50)
);
GO


/* =====================================================
   DIMENSION CREDIT
   Source : OLTP.Credit
===================================================== */

CREATE TABLE Dim_Credit
(
    Credit_Key       INT IDENTITY(1,1) PRIMARY KEY,

    Type_Credit      VARCHAR(50),

    Montant          DECIMAL(15,2),

    Duree_Mois       INT,

    Taux_Interet     DECIMAL(5,2),

    Date_Debut       DATE,

    Statut           VARCHAR(30)
);
GO


/* =====================================================
   DIMENSION DATE
   Utilisée pour les analyses temporelles
===================================================== */

CREATE TABLE Dim_Date
(
    Date_ID           INT PRIMARY KEY,

    Full_Date         DATE NOT NULL UNIQUE,

    Day_Number        INT,

    Day_Name          VARCHAR(20),

    Week_Number       INT,

    Month_Number      INT,

    Month_Name        VARCHAR(20),

    Quarter_Number    INT,

    Year_Number       INT,

    Is_Weekend        BIT DEFAULT 0
);
GO


/* =====================================================
   FACT TABLE : FACT_DATA_QUALITY_ACCURACY

   Suivi des erreurs de qualité des données
   Focus : Accuracy

   Domaines :
   - Client
   - Compte
   - Transaction
   - Credit
===================================================== */

CREATE TABLE Fact_Accuracy
(
    /* =================================================
       KEY TECHNIQUE
    ================================================= */

    Accuracy_Key BIGINT IDENTITY(1,1) PRIMARY KEY,


    /* =================================================
       DIMENSION KEYS

       NULL = la règle ne concerne pas ce domaine
    ================================================= */

    Date_Key INT NOT NULL,

    Client_Key INT NOT NULL,

    Agence_Key INT NOT NULL,

    Compte_Key INT NULL,

    Transaction_Key BIGINT NULL,

    Credit_Key INT NULL,


    /* =================================================
       IDENTIFICATION DE L'ERREUR
    ================================================= */

    Ligne_Id BIGINT NOT NULL,

    Table_Name VARCHAR(100) NOT NULL,

    Column_Name VARCHAR(100) NOT NULL,


    /* =================================================
       VALEUR ET DESCRIPTION DE L'ERREUR
    ================================================= */

    Valeur_Erreur VARCHAR(500),

    Valeur_Attendue VARCHAR(500),

    Error_Message VARCHAR(500),


    /* =================================================
       CLASSIFICATION DATA QUALITY
    ================================================= */

    Issue_Category VARCHAR(100),

    Severity VARCHAR(20),

    Business_Impact VARCHAR(500),


    /* =================================================
       DATE DE DETECTION
    ================================================= */

    Date_Detection DATETIME NOT NULL
        DEFAULT GETDATE(),


    /* =================================================
       FOREIGN KEYS
    ================================================= */

    CONSTRAINT FK_Date
        FOREIGN KEY (Date_Key)
        REFERENCES Dim_Date(Date_ID),

    CONSTRAINT FK_Client
        FOREIGN KEY (Client_Key)
        REFERENCES Dim_Client(Client_Key),

    CONSTRAINT FK_Agence
        FOREIGN KEY (Agence_Key)
        REFERENCES Dim_Agence(Agence_Key),

    CONSTRAINT FK_Compte
        FOREIGN KEY (Compte_Key)
        REFERENCES Dim_Compte(Compte_Key),

    CONSTRAINT FK_Transaction
        FOREIGN KEY (Transaction_Key)
        REFERENCES Dim_Transaction(Transaction_Key),

    CONSTRAINT FK_Credit
        FOREIGN KEY (Credit_Key)
        REFERENCES Dim_Credit(Credit_Key)
);
GO