# PrimeTech — Fiscalité

Module Odoo 18 de préparation fiscale. Il consolide les sources réellement validées de l’instance : comptabilité, factures clients, Point de Vente, règlements et, lorsqu’il est installé, le module de paie.

## Principes

- Les règles indiquent une source, les journaux et/ou les comptes réellement concernés ; aucun compte n’est imposé.
- Les factures liées à des commandes POS sont exclues du flux Facturation afin d’éviter le double comptage.
- Les précomptes importés depuis les comptes comptables et les crédits restent non déductibles tant qu’un utilisateur autorisé ne les a pas validés.
- Une déclaration validée conserve un instantané de sa période, de sa règle et de ses totaux.

## Utilisation

1. Paramétrez vos règles et vos périodes fiscales.
2. Ouvrez une déclaration, calculez les lignes depuis la source choisie et contrôlez les pièces.
3. Importez puis validez les précomptes admissibles ; imputez les crédits admissibles.
4. Faites passer la déclaration par Brouillon → Calculée → En vérification → Validée → Déclarée.

Le tableau de bord Fiscalité est responsive, filtrable par période et se rafraîchit automatiquement selon le délai défini dans Paramètres › Facturation.
