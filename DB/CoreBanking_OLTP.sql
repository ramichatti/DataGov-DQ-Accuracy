CREATE DATABASE CoreBanking_OLTP;
GO

USE CoreBanking_OLTP;
GO


/* =====================================================
   TABLE AGENCE
===================================================== */

CREATE TABLE Agence
(
    Agence_ID INT PRIMARY KEY,
    Code_Agence VARCHAR(20) UNIQUE NOT NULL,
    Nom_Agence VARCHAR(100) NOT NULL,
    Ville VARCHAR(50),
    Adresse VARCHAR(200),
    Telephone VARCHAR(20)
);



/* =====================================================
   TABLE TYPE CLIENT
===================================================== */

CREATE TABLE Type_Client
(
    Type_Client_ID INT PRIMARY KEY,
    Libelle VARCHAR(50) NOT NULL
);



/* =====================================================
   TABLE CLIENT
===================================================== */

CREATE TABLE Client
(
    Client_ID INT PRIMARY KEY,
    CIN VARCHAR(8) UNIQUE NOT NULL,
    Nom VARCHAR(50) NOT NULL,
    Prenom VARCHAR(50) NOT NULL,
    Date_Naissance DATE,
    Email VARCHAR(100),
    Telephone VARCHAR(20),
    Adresse VARCHAR(200),
    Ville VARCHAR(50),
    Type_Client_ID INT,
    Date_Creation DATE,
    Agence_ID INT,

    CONSTRAINT FK_Client_TypeClient
    FOREIGN KEY(Type_Client_ID)
    REFERENCES Type_Client(Type_Client_ID),

    CONSTRAINT FK_Client_Agence
    FOREIGN KEY(Agence_ID)
    REFERENCES Agence(Agence_ID)
);



/* =====================================================
   TABLE DEVISE
===================================================== */

CREATE TABLE Devise
(
    Devise_ID INT PRIMARY KEY,
    Code_Devise VARCHAR(10) UNIQUE,
    Libelle VARCHAR(50)
);



/* =====================================================
   TABLE TYPE COMPTE
===================================================== */

CREATE TABLE Type_Compte
(
    Type_Compte_ID INT PRIMARY KEY,
    Libelle VARCHAR(50),
    Description VARCHAR(200)
);



/* =====================================================
   TABLE COMPTE
===================================================== */

CREATE TABLE Compte
(
    Compte_ID INT PRIMARY KEY,
    Numero_Compte VARCHAR(30) UNIQUE NOT NULL,

    Client_ID INT,
    Type_Compte_ID INT,
    Devise_ID INT,

    Solde DECIMAL(15,2),
    Date_Ouverture DATE,
    Statut VARCHAR(20),


    CONSTRAINT FK_Compte_Client
    FOREIGN KEY(Client_ID)
    REFERENCES Client(Client_ID),


    CONSTRAINT FK_Compte_Type
    FOREIGN KEY(Type_Compte_ID)
    REFERENCES Type_Compte(Type_Compte_ID),


    CONSTRAINT FK_Compte_Devise
    FOREIGN KEY(Devise_ID)
    REFERENCES Devise(Devise_ID)
);



/* =====================================================
   TABLE CARTE BANCAIRE
===================================================== */

CREATE TABLE Carte
(
    Carte_ID INT PRIMARY KEY,
    Compte_ID INT,

    Numero_Carte VARCHAR(16) UNIQUE,
    Type_Carte VARCHAR(30),
    Date_Expiration DATE,
    Statut VARCHAR(20),


    CONSTRAINT FK_Carte_Compte
    FOREIGN KEY(Compte_ID)
    REFERENCES Compte(Compte_ID)
);



/* =====================================================
   TABLE CANAL TRANSACTION
===================================================== */

CREATE TABLE Canal_Transaction
(
    Canal_ID INT PRIMARY KEY,
    Libelle VARCHAR(50)
);



/* =====================================================
   TABLE TRANSACTION BANCAIRE
===================================================== */

CREATE TABLE Transaction_Bancaire
(
    Transaction_ID BIGINT PRIMARY KEY,

    Compte_ID INT,
    Canal_ID INT,

    Type_Transaction VARCHAR(50),
    Montant DECIMAL(15,2),

    Date_Transaction DATETIME,

    Reference_Transaction VARCHAR(50),


    CONSTRAINT FK_Transaction_Compte
    FOREIGN KEY(Compte_ID)
    REFERENCES Compte(Compte_ID),


    CONSTRAINT FK_Transaction_Canal
    FOREIGN KEY(Canal_ID)
    REFERENCES Canal_Transaction(Canal_ID)
);



/* =====================================================
   TABLE CREDIT
===================================================== */

CREATE TABLE Credit
(
    Credit_ID INT PRIMARY KEY,

    Client_ID INT,

    Type_Credit VARCHAR(50),

    Montant DECIMAL(15,2),

    Duree_Mois INT,

    Taux_Interet DECIMAL(5,2),

    Date_Debut DATE,

    Statut VARCHAR(30),


    CONSTRAINT FK_Credit_Client
    FOREIGN KEY(Client_ID)
    REFERENCES Client(Client_ID)
);



/* =====================================================
   TABLE REMBOURSEMENT
===================================================== */

CREATE TABLE Remboursement
(
    Remboursement_ID INT PRIMARY KEY,

    Credit_ID INT,

    Date_Paiement DATE,

    Montant_Paye DECIMAL(15,2),

    Statut VARCHAR(20),


    CONSTRAINT FK_Remboursement_Credit
    FOREIGN KEY(Credit_ID)
    REFERENCES Credit(Credit_ID)
);



/* =====================================================
   TABLE VIREMENT
===================================================== */

CREATE TABLE Virement
(
    Virement_ID BIGINT PRIMARY KEY,

    Compte_Source_ID INT,

    Compte_Destination_ID INT,

    Montant DECIMAL(15,2),

    Date_Virement DATETIME,

    Statut VARCHAR(20),


    CONSTRAINT FK_Virement_Source
    FOREIGN KEY(Compte_Source_ID)
    REFERENCES Compte(Compte_ID),


    CONSTRAINT FK_Virement_Destination
    FOREIGN KEY(Compte_Destination_ID)
    REFERENCES Compte(Compte_ID)
);



/* =====================================================
   TABLE HISTORIQUE SOLDE
===================================================== */

CREATE TABLE Historique_Solde
(
    Historique_ID BIGINT PRIMARY KEY,

    Compte_ID INT,

    Ancien_Solde DECIMAL(15,2),

    Nouveau_Solde DECIMAL(15,2),

    Date_Modification DATETIME,


    CONSTRAINT FK_Historique_Compte
    FOREIGN KEY(Compte_ID)
    REFERENCES Compte(Compte_ID)
);



/* =====================================================
   TABLE EMPLOYE
===================================================== */

CREATE TABLE Employe
(
    Employe_ID INT PRIMARY KEY,

    Nom VARCHAR(50),

    Prenom VARCHAR(50),

    Fonction VARCHAR(50),

    Email VARCHAR(100),

    Agence_ID INT,


    CONSTRAINT FK_Employe_Agence
    FOREIGN KEY(Agence_ID)
    REFERENCES Agence(Agence_ID)
);



/* =====================================================
   TABLE AUDIT LOG
===================================================== */

CREATE TABLE Audit_Log
(
    Audit_ID BIGINT PRIMARY KEY,

    Table_Nom VARCHAR(100),

    Operation VARCHAR(30),

    Utilisateur VARCHAR(50),

    Date_Action DATETIME,

    Description VARCHAR(250)
);


GO