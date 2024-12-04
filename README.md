# Media Finder

## Guide d’utilisation

## 1. Clonage du dépôt

Clonez le projet sur votre machine locale :

```bash
git clone https://github.com/AliBay07/media-finder.git
cd media-finder
```

## 2. Test de l'application avec Docker

La façon la plus simple de tester l'application est d'utiliser Docker. Suivez ces étapes pour démarrer et tester l'application avec Docker.

### Prérequis

Pour exécuter cette application, vous devez avoir **Docker** installé sur votre machine. Voici comment installer Docker sur différents systèmes d'exploitation.

### Installation de Docker

#### Sur Windows

1. Téléchargez Docker Desktop pour Windows à partir du site officiel :  
   [Docker Desktop pour Windows](https://www.docker.com/products/docker-desktop/)
2. Suivez les instructions d'installation de Docker Desktop.
3. Une fois l'installation terminée, ouvrez Docker Desktop et vérifiez qu'il fonctionne correctement.

#### Sur Linux

Sur Linux, Docker peut être installé via le terminal. Voici les commandes à utiliser pour une installation sur **Ubuntu** :

```bash
sudo apt update

sudo apt install apt-transport-https ca-certificates curl software-properties-common

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

sudo apt update

sudo apt install docker-ce

sudo apt install docker-compose

docker --version
docker-compose --version

```

Assurez-vous que Docker fonctionne correctement après l'installation :

```bash
sudo systemctl start docker
sudo systemctl enable docker
```

#### Sur macOS

1. Téléchargez Docker Desktop pour macOS à partir du site officiel :
   [Docker Desktop pour macOS](https://docs.docker.com/desktop/setup/install/mac-install/)
2. Suivez les instructions d'installation de Docker Desktop.
3. Après l'installation, ouvrez Docker Desktop et vérifiez qu'il fonctionne correctement.

### 1. Lancer l'application avec Docker

Dans le répertoire du projet, exécutez la commande suivante pour démarrer les conteneurs Docker nécessaires à l'application et au serveur Fuseki :

```bash
docker-compose up --build
```

Cela va construire les images Docker et démarrer les conteneurs pour le serveur Fuseki et l'application Streamlit.

### 2. Accéder à l'application

Une fois Docker en cours d'exécution, vous pouvez accéder à l'application via un navigateur web en utilisant l'URL suivante :

```bash
http://localhost:8501
```

Cela ouvrira l'application Streamlit, et vous pourrez commencer à interagir avec l'interface utilisateur.

### 3. Arrêter l'application

Pour arrêter les conteneurs Docker, utilisez la commande suivante :

```bash
docker-compose down
```

## 3. Test de l'application sans Docker

### 1. Configuration d'Apache Jena Fuseki

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

Retourner dans le dossier app :

```bash
cd ..
```

Installez les dépendances nécessaires :

```bash
pip install -r requirements.txt
```

### 4. Lancement de l'application

#### 1. Lancez l'application avec la commande suivante :

```bash
streamlit run app.py
```

## 4. Test de l'application

Voici quelques exemples pour tester le fonctionnement de l’application :

#### 1. Recherche de morceaux

- Utilisez la fonctionnalité de recherche pour trouver un morceau par son nom.
- Par exemple, recherchez le morceau "wish".
- Explorez les informations récupérées pour accéder à d’autres fonctionnalités, comme rechercher l’album ou l’artiste associé.

#### 2. Recherche d’images

- Ajoutez des images dans la base de données. Par exemple, ajoutez les images disponibles dans le dossier media-finder/images.
- Effectuez une recherche avec le mot-clé "dog".
- Les images contenant des chiens que vous avez ajoutées apparaîtront.
