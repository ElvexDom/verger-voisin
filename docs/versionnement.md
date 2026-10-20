# Règles de versionnement

Ce document fixe comment on utilise Git et GitHub dans Verger Voisin : branches, messages de
commit, lien entre commits et tickets, vie d'un ticket de tâche et d'un ticket d'incident.
Le dépôt est **public** : tout ce qui est poussé est visible de tous (voir la section 7).

Un seul contributeur (Nikko) : les règles sont volontairement simples.

## 1. Principes

- **Langue** : les messages de commit, les tickets et la documentation sont en français.
- **Une branche par ticket** : tout travail part d'un ticket GitHub.
- **`main` reste propre** : on ne commite pas directement dessus (règle d'habitude, pas de
  protection technique). On y revient uniquement par fusion d'une demande de fusion (pull request).
  Seule exception : le tout premier commit du dépôt.
- **Rien de secret ni de volumineux** : jamais de `.env`, de mot de passe, de jeton, de
  données ou de dump de base dans un commit.

## 2. Les branches

| Branche | Rôle | Nommage |
|---|---|---|
| `main` | Version stable et à jour du projet, celle que le VPS récupère | `main` |
| Branche de tâche | Réaliser un ticket de tâche | `tache/<numéro>-<description-courte>` |
| Branche d'incident | Corriger un incident | `incident/<numéro>-<description-courte>` |

Règles de nommage : minuscules, mots séparés par des tirets, sans accent ni espace.
Exemples : `tache/12-script-extraction-api`, `incident/27-erreur-connexion-postgres`.

Les branches sont courtes : on les supprime après la fusion.

## 3. Les messages de commit

Format :

```
<Résumé à l'infinitif ou au présent, 72 caractères au plus> (#<numéro du ticket>)

Explication facultative : pourquoi ce changement (pas le détail du code).
```

Exemples :

```
Ajouter le script de contrôle de PostgreSQL (#12)
Corriger la lecture du port dans le .env (#27)
```

- Un commit = un changement cohérent. Éviter les commits fourre-tout.
- Le numéro du ticket est toujours à la fin de la première ligne.
- Pas de secret, pas de donnée personnelle, pas d'adresse e-mail dans le message.

## 4. Lier commits, branches et tickets

- **Dans un commit** : écrire `(#12)` dans le message. GitHub affiche alors le commit dans la
  chronologie du ticket n° 12.
- **Dans la demande de fusion** : écrire `Closes #12` dans la description (le gabarit est déjà
  prérempli). Le mot-clé doit rester en anglais (`Closes`, `Fixes`, `Resolves`) : GitHub ferme
  alors automatiquement le ticket à la fusion dans `main`.
- **Dans un ticket** : citer `#12` dans un commentaire crée un lien vers l'autre ticket.

## 5. Vie d'un ticket

### Ticket de tâche (modèle « Tâche », étiquette `tache`)

1. **Ouverture** : créer le ticket avec le modèle « Tâche » (objectif, critères de réussite).
2. **Travail** : créer la branche `tache/<numéro>-...`, faire des commits `... (#numéro)`.
3. **Demande de fusion** : pousser la branche, ouvrir une demande de fusion vers `main` avec
   `Closes #numéro`. Relire les fichiers modifiés (aucun secret).
4. **Fusion** : choisir « Create a merge commit » (garde les commits visibles depuis le ticket),
   puis supprimer la branche.
5. **Clôture** : le ticket se ferme tout seul. Vérifier que les critères de réussite sont cochés.

### Ticket d'incident (modèle « Incident », étiquette `incident`)

Un incident est un problème technique constaté. Le ticket sert de journal de débogage : il
alimentera la documentation de la résolution (compétence C21).

1. **Ouverture dès la constatation** : symptôme, contexte, étapes pour reproduire (sans secret).
2. **Analyse** : chaque hypothèse testée et chaque résultat est ajouté en commentaire, avec la
   date. Ne pas effacer les pistes qui n'ont pas marché.
3. **Reproduction** : confirmer que le problème est reproduit en environnement de
   développement et le noter dans le ticket.
4. **Correctif** : branche `incident/<numéro>-...`, commits `... (#numéro)`, ajout d'un test
   qui échouait avant le correctif et réussit après (quand c'est possible).
5. **Demande de fusion et fusion** : comme pour une tâche, avec `Closes #numéro`.
6. **Clôture** : compléter la section « Résolution » (cause, correctif, vérification,
   prévention) avant ou juste après la fermeture.

### Étiquettes à créer dans GitHub

Dans l'onglet *Issues* puis *Labels*, créer `tache` et `incident` (les modèles les utilisent).
Une étiquette `bug` peut s'ajouter pour un défaut mineur qui ne mérite pas un incident complet.

## 6. Procédure pas à pas : tester le lien commit - ticket

À faire une fois, pour vérifier que tout est en place. Hypothèse : le dépôt est déjà créé sur
GitHub et le dossier `verger-voisin/` de ton poste est relié à lui (voir `README.md`, section
« Le circuit »). Ces commandes se lancent sur **ton poste**, là où tu pousses vers GitHub : le
VPS, lui, ne fait que `git pull` et n'a donc pas besoin de droits d'écriture sur GitHub.

1. **Sur GitHub** : créer un ticket avec le modèle « Tâche », titre « Test du lien commit-ticket ».
   Noter son numéro, par exemple `1`. *Résultat attendu* : le ticket existe avec l'étiquette `tache`.
2. **Dans le dossier `verger-voisin/` de ton poste** :
   ```bash
   git switch main
   git pull
   git switch -c tache/1-test-versionnement
   ```
   *Résultat attendu* : `Switched to a new branch 'tache/1-test-versionnement'`.
3. **Faire un commit de test** (sans modifier de fichier) :
   ```bash
   git commit --allow-empty -m "Tester le lien entre commit et ticket (#1)"
   git push -u origin tache/1-test-versionnement
   ```
   *Résultat attendu* : le commit est créé, puis la branche apparaît sur GitHub.
4. **Retrouver le commit depuis le ticket** : ouvrir le ticket n° 1 sur GitHub.
   *Résultat attendu* : une ligne dans la chronologie indique que le commit
   « Tester le lien entre commit et ticket (#1) » fait référence au ticket.
   *Constaté le 2026-10-20 (ticket n° 1)* : tant que la branche n'est pas fusionnée, le commit
   n'apparaît pas dans le ticket. C'est l'étape 5 qui crée le lien : après la fusion, la
   chronologie du ticket montre la demande de fusion, le commit de fusion qui le cite, et la
   fermeture automatique.
5. **Ouvrir une demande de fusion** vers `main` avec `Closes #1` dans la description, la fusionner
   (« Create a merge commit »), supprimer la branche. *Résultat attendu* : le ticket n° 1 est
   fermé automatiquement et la demande de fusion est visible dans sa chronologie.
6. **Mettre à jour la copie locale** :
   ```bash
   git switch main
   git pull
   git branch -d tache/1-test-versionnement
   ```
   *Résultat attendu* : `Deleted branch tache/1-test-versionnement`.

*Si ça échoue* : `git push` refusé -> vérifier la connexion à GitHub depuis ton poste
(`git remote -v` doit montrer l'adresse du dépôt). Le commit n'apparaît pas dans le ticket ->
vérifier que le numéro est bien écrit `#1` dans le message (`git log -1`).

Pour que le VPS reçoive ensuite la version fusionnée : `git pull` dans le dépôt cloné sur le VPS.

## 7. Dépôt public : garde-fous

Le dépôt GitHub est public. **Avant chaque `git push`** :

1. `git status` : le `.env` et le contenu de `donnees/` ou `journaux/` ne doivent pas apparaître.
2. `git diff --staged` : relire ce qui va partir (mot de passe, jeton, adresse e-mail ?).
3. Ne jamais utiliser `git add .` sans avoir fait l'étape 1.

Si un secret a quand même été poussé : le considérer comme compromis, **le changer
immédiatement** (nouveau mot de passe dans `.env` et dans PostgreSQL), puis demander de l'aide
avant de toucher à l'historique Git (réécriture risquée).

Adresse e-mail des commits : Git l'écrit dans chaque commit, et un dépôt public la montre.
Pour ne pas exposer une adresse personnelle, GitHub propose une adresse de redirection
(réglages du compte, section « Emails »), à renseigner avec
`git config user.email "<adresse fournie par GitHub>"`.
