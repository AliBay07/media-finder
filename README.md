# Media Finder

## Guide d’utilisation

### 1. Clonage du dépôt
Clonez le projet sur votre machine locale :
```bash
git clone https://github.com/AliBay07/media-finder.git
cd media-finder
```

### 2. Configuration d'Apache Jena Fuseki

### Lancer le serveur :

#### 1. Naviguer vers le répertoire contenant Apache Jena Fuseki :

```bash
cd app/apache-jena-fuseki-5.2.0
```

#### 2. Démarrez le serveur :

```bash
./run.sh
```

#### 3. Ouvrez l'interface web dans un navigateur en accédant à :

```bash
http://localhost:3030
```

### Création et configuration de la base de données :

#### 1. Dans l'interface Fuseki, cliquez sur "add one"

#### 2. Nommez le dataset : media-finder.

##### 3. Cliquez sur "create database".

##### 4. Ajoutez les données :

- Cliquez sur "add data".
- Importez le fichier media_ontology.ttl situé dans le dossier turtle.

### 3. Installation des dépendances Python 

Installez les dépendances nécessaires :

```bash
pip install -r requirements.txt
```

### 4. Lancement de l'application
#### 1. Naviguez vers le répertoire contenant l'application Streamlit :
```bash
cd app
```

#### 2. Lancez l'application avec la commande suivante :
```bash
streamlit run app.py
```