# Règles de Qualité des Données (Data Quality Rules)

## Client

| # | Règle | Colonne | Description | Séverité | Valeur Attendue |
|---|-------|---------|-------------|----------|-----------------|
| 1 | **Format CIN Tunisien** | `CIN` | Le CIN doit contenir exactement 8 chiffres (format de la carte d'identité nationale tunisienne) | Haute | 8 digits (Tunisian format) |
| 2 | **Format Téléphone Tunisien** | `Telephone` | Le numéro de téléphone doit commencer par `+216` ou `00216` suivi de 8 chiffres | Haute | +216 or 00216 followed by 8 digits |
| 3 | **Format Email** | `Email` | L'email doit respecter le format standard avec `@` et une extension de domaine | Moyenne | Valid email format (user@domain.extension) |
| 4 | **Date de Naissance Valide** | `Date_Naissance` | La date de naissance ne doit pas être dans le futur, ni avant 1900, et le client doit avoir au moins 18 ans | Haute | Between 1900-01-01 and 18 years ago |
| 5 | **Ville Manquante** | `Ville` | Si une adresse est renseignée, la ville ne doit pas être vide | Moyenne | Ville should not be empty when Adresse is provided |
| 6 | **Cohérence Âge / Type Client** | `Date_Naissance` | Un client de type `Entreprise` ou `Coopérative` doit être majeur (≥ 18 ans) | Haute | Company-type clients must be 18+ |

### Explications

**Règle 1** — Le CIN tunisien est un identifiant national unique de 8 chiffres. Toute valeur ne respectant pas ce format (lettres, chiffres manquants) est considérée comme erronée.

**Règle 2** — Les numéros de téléphone tunisiens valides commencent par l'indicatif `+216` ou `00216` suivis de 8 chiffres (ex: `+21699123456`). Les numéros étrangers ou formats incorrects sont signalés.

**Règle 3** — Vérifie que l'email contient un `@` et un nom de domaine avec extension (ex: `user@domain.com`).

**Règle 4** — Vérifie la plausibilité de la date de naissance : pas de date future, pas de date antérieure à 1900, et âge minimum de 18 ans pour être titulaire d'un compte.

**Règle 5** — Cohérence géographique : si une adresse physique est fournie, la ville doit également être renseignée.

**Règle 6** — Une entreprise ou coopérative est nécessairement gérée par une personne majeure. Un client mineur avec ce type est incohérent.

---

## Compte

| # | Règle | Colonne | Description | Séverité | Valeur Attendue |
|---|-------|---------|-------------|----------|-----------------|
| 1 | **Solde Extrême** | `Solde` | Le solde ne doit pas dépasser 1 milliard en valeur absolue, et doit être ≥ 0.01 (sauf si 0) | Haute | Between -1B and 1B, minimum 0.01 precision |
| 2 | **Précision Décimale du Solde** | `Solde` | Le solde ne doit pas dépasser 3 décimales (précision monétaire standard) | Moyenne | Maximum 3 decimal places |
| 3 | **Date d'Ouverture Valide** | `Date_Ouverture` | La date d'ouverture ne doit pas être dans le futur ni avant 1950 | Haute | Between 1950-01-01 and current date |
| 4 | **Cohérence Statut / Solde** | `Statut` | Un compte clôturé (`Cloture`) doit avoir un solde à zéro | Haute | Closed accounts should have zero balance |
| 5 | **Format Numéro de Compte** | `Numero_Compte` | Le numéro de compte doit contenir au moins 10 caractères | Moyenne | Account number must be at least 10 characters |
| 6 | **Compte sans Client** | `Client_ID` | Chaque compte doit être rattaché à un client | Haute | Each account must have an assigned client |

### Explications

**Règle 1** — Les soldes extrêmes (≥ 1Md) ou anormalement bas (entre 0 et 0.01) indiquent probablement des erreurs de saisie.

**Règle 2** — Les montants monétaires sont généralement limités à 2 ou 3 décimales. Au-delà, il s'agit probablement d'une erreur d'arrondi ou de saisie.

**Règle 3** — La banque n'existait pas avant 1950, et une date d'ouverture future est impossible.

**Règle 4** — Règle métier : un compte clôturé ne devrait pas avoir de solde restant. Cela indique une incohérence dans les données.

**Règle 5** — Les numéros de compte bancaires suivent un format standard d'au moins 10 caractères. Un numéro trop court est suspect.

**Règle 6** — Tout compte doit être associé à un client. Un compte orphelin est une anomalie.

---

## Transaction Bancaire

| # | Règle | Colonne | Description | Séverité | Valeur Attendue |
|---|-------|---------|-------------|----------|-----------------|
| 1 | **Montant Extrême** | `Montant` | Le montant de la transaction ne doit pas dépasser 100 millions en valeur absolue | Haute | Between -100M and 100M |
| 2 | **Précision Décimale du Montant** | `Montant` | Le montant ne doit pas dépasser 3 décimales | Moyenne | Maximum 3 decimal places |
| 3 | **Date de Transaction Valide** | `Date_Transaction` | La date de transaction doit être entre 2000 et la date actuelle | Haute | Between 2000-01-01 and current date |
| 4 | **Cohérence Type / Montant** | `Montant` | Un virement (`Virement`) doit avoir un montant positif | Haute | Virement transactions must have positive amount |
| 5 | **Transaction sans Référence** | `Reference_Transaction` | Chaque transaction doit avoir une référence | Moyenne | Each transaction must have a reference |
| 6 | **Transaction sur Compte Clôturé** | `Compte_ID` | Aucune transaction ne doit être postée sur un compte clôturé | Haute | No transactions allowed on closed accounts |

### Explications

**Règle 1** — Une transaction de plus de 100M est considérée comme extrême et potentiellement erronée.

**Règle 2** — Même principe que pour le solde des comptes : pas plus de 3 décimales pour un montant monétaire.

**Règle 3** — Les transactions avant l'an 2000 ou dans le futur sont considérées comme invalides.

**Règle 4** — Un virement ne peut pas avoir un montant négatif ou nul par nature. Cela indique une erreur de saisie.

**Règle 5** — Toute transaction doit avoir une référence unique pour le suivi et l'audit.

**Règle 6** — Un compte clôturé ne peut plus recevoir de transactions. C'est une règle métier fondamentale.

---

## Credit

| # | Règle | Colonne | Description | Séverité | Valeur Attendue |
|---|-------|---------|-------------|----------|-----------------|
| 1 | **Montant Extrême** | `Montant` | Le montant du crédit doit être entre 100 et 10 millions | Haute | Between 100 and 10M |
| 2 | **Précision Décimale du Montant** | `Montant` | Le montant ne doit pas dépasser 3 décimales | Moyenne | Maximum 3 decimal places |
| 3 | **Taux d'Intérêt Hors Plage** | `Taux_Interet` | Le taux d'intérêt doit être entre 2% et 25% (marché tunisien) | Haute | Between 2% and 25% (Tunisian market rates) |
| 4 | **Date de Début Valide** | `Date_Debut` | La date de début ne doit pas être dans le futur ni avant 2000 | Haute | Between 2000-01-01 and current date |
| 5 | **Cohérence Montant / Durée** | `Montant` | La mensualité calculée (Montant / Duree_Mois) doit être ≥ 10 | Haute | Monthly payment should be at least 10 |
| 6 | **Crédit sans Client** | `Client_ID` | Chaque crédit doit être rattaché à un client | Haute | Each credit must have an assigned client |
| 7 | **Durée Anormale** | `Duree_Mois` | La durée du crédit doit être entre 1 et 360 mois (30 ans max) | Haute | Duration must be between 1 and 360 months (30 years) |

### Explications

**Règle 1** — Un crédit de moins de 100 ou de plus de 10 millions est considéré comme extrême et potentiellement erroné.

**Règle 2** — Même principe que pour les autres montants : pas plus de 3 décimales.

**Règle 3** — Les taux d'intérêt sur le marché tunisien sont généralement compris entre 2% et 25%. En dehors de cette fourchette, il s'agit probablement d'une erreur.

**Règle 4** — Un crédit ne peut pas avoir une date de début avant 2000 (marché moderne) ni dans le futur.

**Règle 5** — La mensualité estimée (montant total / durée en mois) doit être réaliste. Une mensualité inférieure à 10 est suspecte.

**Règle 6** — Tout crédit doit être associé à un client. Un crédit orphelin est une anomalie.

**Règle 7** — La durée d'un crédit ne peut pas dépasser 30 ans (360 mois) ni être inférieure à 1 mois.
