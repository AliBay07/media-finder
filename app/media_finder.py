from SPARQLWrapper import SPARQLWrapper, POST, JSON
import tensorflow as tf
import cv2
import numpy as np
from PIL import Image
import random
import uuid
import base64
import io
import os
import rdflib
import requests
import time


class MediaFinder:

    def __init__(self, base_url):
        self.base_url = base_url
        self.dataset_name = "media-finder"
        self.auth = ("admin", "password")
        self.sparql = None
        self.wait_for_fuseki(self.base_url)
        self.setup_database()

        self.sparql = SPARQLWrapper(f"{self.base_url}/{self.dataset_name}/")

        model_path = "ssd_mobilenet_v2_coco_2018_03_29/saved_model"
        self.model = tf.saved_model.load(model_path)
        self.detect_fn = self.model.signatures['serving_default']

        self.COCO_LABELS = [
            'N/A', 'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat',
            'traffic light', 'fire hydrant', 'N/A', 'stop sign', 'parking meter', 'bench', 'bird', 'cat',
            'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'N/A', 'backpack',
            'umbrella', 'N/A', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
            'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket', 'bottle',
            'N/A', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich',
            'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch', 'potted plant',
            'bed', 'N/A', 'dining table', 'N/A', 'toilet', 'N/A', 'tv', 'laptop', 'mouse', 'remote', 'keyboard',
            'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book', 'clock', 'vase',
            'scissors', 'teddy bear', 'hair drier', 'toothbrush'
        ]

    def wait_for_fuseki(self, base_url, timeout=60):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{base_url}/$/ping")
                if response.status_code == 200:
                    return
            except requests.ConnectionError:
                time.sleep(2)
        raise RuntimeError("Fuseki server did not become ready in time.")

    def setup_database(self):
        admin_url = f"{self.base_url}/$/datasets"
        turtle_file_path = "media_ontology.ttl"

        response = requests.post(
            admin_url,
            data={"dbName": self.dataset_name, "dbType": "tdb2"},
            auth=self.auth
        )
        if response.status_code not in [200, 409]:
            raise RuntimeError(f"Failed to create dataset: {response.reason}")

        dataset_url = f"{self.base_url}/{self.dataset_name}/data"
        if os.path.exists(turtle_file_path):
            with open(turtle_file_path, "r") as turtle_file:
                turtle_data = turtle_file.read()
            response = requests.post(
                dataset_url,
                data=turtle_data,
                headers={"Content-Type": "text/turtle"},
                auth=self.auth
            )
            if response.status_code != 200:
                raise RuntimeError(f"Failed to load data: {response.reason}")

    def detect_objects(self, image):
        """
        Detect objects in the uploaded image and return the image with bounding boxes and object labels.
        """
        image_rgb = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        input_tensor = tf.convert_to_tensor(image_rgb)
        input_tensor = input_tensor[tf.newaxis, ...]

        detections = self.detect_fn(input_tensor)

        boxes = detections['detection_boxes'].numpy()[0]
        class_ids = detections['detection_classes'].numpy()[0].astype(int)
        scores = detections['detection_scores'].numpy()[0]

        detected_objects = []

        for i in range(len(scores)):
            if scores[i] > 0.5:
                box = boxes[i]
                (ymin, xmin, ymax, xmax) = box
                xmin = int(xmin * image.size[0])
                ymin = int(ymin * image.size[1])
                xmax = int(xmax * image.size[0])
                ymax = int(ymax * image.size[1])

                color = tuple([random.randint(0, 255) for _ in range(3)])

                cv2.rectangle(image_rgb, (xmin, ymin), (xmax, ymax), color, 2)

                class_name = self.COCO_LABELS[class_ids[i]]
                label = f"{class_name}: {scores[i]:.2f}"

                cv2.putText(image_rgb, label, (xmin, ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)

                detected_objects.append(class_name)

        result_image = Image.fromarray(cv2.cvtColor(image_rgb, cv2.COLOR_BGR2RGB))

        return result_image, detected_objects

    def save_image_to_triplestore(self, image, detected_objects):
        """
        Save the image along with its detected objects' data to the triple store.
        """
        image_uri = f"<http://mediafinder.org/media/{str(uuid.uuid5(uuid.NAMESPACE_DNS, str(image.tobytes())))}>"

        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        insert_query = f"""
        PREFIX media: <http://mediafinder.org/media/>
        PREFIX property: <http://mediafinder.org/properties/>
        
        INSERT DATA {{
             {image_uri} a <http://mediafinder.org/media/Image> ;
                <http://mediafinder.org/properties/base64Value> "{image_base64}" ;
        """

        for i, detected_object in enumerate(detected_objects):
            if i == len(detected_objects) - 1:
                insert_query += f'        <http://mediafinder.org/properties/containsObject> "{detected_object}" .\n'
            else:
                insert_query += f'        <http://mediafinder.org/properties/containsObject> "{detected_object}" ;\n'

        insert_query += "}"

        self.sparql.setQuery(insert_query)
        self.sparql.setMethod(POST)

        self.sparql.query()

    def search_for_images(self, detected_object):
        """
        Search for images in the triplestore based on detected objects.
        """
        search_query = f"""
        PREFIX media: <http://mediafinder.org/media/>
        PREFIX property: <http://mediafinder.org/properties/>

        SELECT ?image ?containsObject ?base64Value
        WHERE {{
            ?image a media:Image ;
                property:containsObject ?containsObject ;
                property:base64Value ?base64Value .
            FILTER(CONTAINS(?containsObject, "{detected_object}"))
        }}
        """

        self.sparql.setQuery(search_query)
        self.sparql.setReturnFormat(JSON)
        results = self.sparql.query().convert()

        return results

    def getTracks(self, filter_var: str, filter_value: str):
        """
        Generic method to fetch track details based on a given filter.

        :param filter_var: The variable to filter on (e.g., "trackName", "artistName", "albumName").
        :param filter_value: The value to filter by.
        :return: A tuple of (construct_result, select_result).
        """
        construct_query = f"""
        PREFIX media: <http://mediafinder.org/media/>
        PREFIX property: <http://mediafinder.org/properties/>

        CONSTRUCT {{
            ?track a media:Track .
            ?track property:trackName ?trackName .
            ?track property:trackDuration ?trackDuration .
            ?track property:trackSpotifyURI ?trackSpotifyURI .
            ?track property:trackHasArtist ?artist .
            ?artist property:artistName ?artistName .
            ?track property:trackBelongsToAlbum ?album .
            ?album property:albumName ?albumName .
            ?track property:trackExplicit ?trackExplicit .
            ?track property:trackISRC ?trackISRC .
            ?track property:trackPopularity ?trackPopularity .
        }}
        WHERE {{
            ?track a media:Track .
            ?track property:trackName ?trackName .
            ?track property:trackDuration ?trackDuration .
            ?track property:trackSpotifyURI ?trackSpotifyURI .
            ?track property:trackHasArtist ?artist .
            ?artist a media:Artist .
            ?artist property:artistName ?artistName .
            ?track property:trackBelongsToAlbum ?album .
            ?album property:albumName ?albumName .
            ?track property:trackExplicit ?trackExplicit .
            ?track property:trackISRC ?trackISRC .
            ?track property:trackPopularity ?trackPopularity .
            FILTER (regex(str(?{filter_var}), "{filter_value}", "i"))
        }}
        """

        select_query = f"""
        PREFIX media: <http://mediafinder.org/media/>
        PREFIX property: <http://mediafinder.org/properties/>

        SELECT ?track ?trackName ?trackDuration ?trackSpotifyURI 
               (GROUP_CONCAT(DISTINCT ?artistName; separator=", ") AS ?artists) 
               ?album ?albumName ?trackExplicit ?trackISRC ?trackPopularity
        WHERE {{
            ?track a media:Track .
            ?track property:trackName ?trackName .
            ?track property:trackDuration ?trackDuration .
            ?track property:trackSpotifyURI ?trackSpotifyURI .
            ?track property:trackHasArtist ?artist .
            ?artist a media:Artist .
            ?artist property:artistName ?artistName .
            ?track property:trackBelongsToAlbum ?album .
            ?album property:albumName ?albumName .
            ?track property:trackExplicit ?trackExplicit .
            ?track property:trackISRC ?trackISRC .
            ?track property:trackPopularity ?trackPopularity .
            FILTER (regex(str(?{filter_var}), "{filter_value}", "i"))
        }}
        GROUP BY ?track ?trackName ?trackDuration ?trackSpotifyURI 
                 ?album ?albumName ?trackExplicit ?trackISRC ?trackPopularity
        """

        self.sparql.setQuery(construct_query)
        self.sparql.setReturnFormat(JSON)
        construct_result = self.sparql.query().convert()

        self.sparql.setQuery(select_query)
        self.sparql.setReturnFormat(JSON)
        select_result = self.sparql.query().convert()

        return construct_result, select_result

    def getAlbum(self, filter_var: str, filter_value: str):
        """
        Generic method to fetch album details based on a given filter.

        :param filter_var: The variable to filter on (e.g., "albumName", "albumSpotifyURI", "albumType").
        :param filter_value: The value to filter by.
        :return: A tuple of (construct_result, select_result).
        """
        construct_query = f"""
        PREFIX media: <http://mediafinder.org/media/>
        PREFIX property: <http://mediafinder.org/properties/>

        CONSTRUCT {{
            ?album a media:Album .
            ?album property:albumName ?albumName .
            ?album property:albumReleaseDate ?albumReleaseDate .
            ?album property:albumSpotifyURI ?albumSpotifyURI .
            ?album property:albumTotalTracks ?albumTotalTracks .
            ?album property:albumType ?albumType .
            ?track a media:Track .
            ?track property:trackName ?trackName .
            ?track property:trackSpotifyURI ?trackSpotifyURI .
            ?track property:trackBelongsToAlbum ?album .
        }}
        WHERE {{
            ?album a media:Album .
            ?album property:albumName ?albumName .
            ?album property:albumReleaseDate ?albumReleaseDate .
            ?album property:albumSpotifyURI ?albumSpotifyURI .
            ?album property:albumTotalTracks ?albumTotalTracks .
            ?album property:albumType ?albumType .
            ?track a media:Track .
            ?track property:trackName ?trackName .
            ?track property:trackSpotifyURI ?trackSpotifyURI .
            ?track property:trackBelongsToAlbum ?album .
            FILTER (regex(str(?{filter_var}), "{filter_value}", "i"))
        }}
        """

        select_query = f"""
        PREFIX media: <http://mediafinder.org/media/>
        PREFIX property: <http://mediafinder.org/properties/>

        SELECT ?album ?albumName ?albumReleaseDate ?albumSpotifyURI ?albumTotalTracks ?albumType
               (GROUP_CONCAT(DISTINCT ?trackName; separator=", ") AS ?tracks)
        WHERE {{
            ?album a media:Album .
            ?album property:albumName ?albumName .
            ?album property:albumReleaseDate ?albumReleaseDate .
            ?album property:albumSpotifyURI ?albumSpotifyURI .
            ?album property:albumTotalTracks ?albumTotalTracks .
            ?album property:albumType ?albumType .
            ?track a media:Track .
            ?track property:trackName ?trackName .
            ?track property:trackSpotifyURI ?trackSpotifyURI .
            ?track property:trackBelongsToAlbum ?album .
            FILTER (regex(str(?{filter_var}), "{filter_value}", "i"))
        }}
        GROUP BY ?album ?albumName ?albumReleaseDate ?albumSpotifyURI ?albumTotalTracks ?albumType
        """

        self.sparql.setQuery(construct_query)
        self.sparql.setReturnFormat(JSON)
        construct_result = self.sparql.query().convert()

        self.sparql.setQuery(select_query)
        self.sparql.setReturnFormat(JSON)
        select_result = self.sparql.query().convert()

        return construct_result, select_result

    def _getDbpediaArtistInfo(self, artist_name: str):
        """
        Fetch artist details from DBpedia based on the artist's name.

        :param artist_name: The name of the artist to fetch information for.
        :return: A tuple of (construct_result, select_result), each in RDF graph or JSON format.
        """
        dbpedia_endpoint = "https://dbpedia.org/sparql"

        artist_name_for_request = artist_name.replace(" ", "_")

        construct_query = f"""
                PREFIX dbo: <http://dbpedia.org/ontology/>
                PREFIX foaf: <http://xmlns.com/foaf/0.1/>

                CONSTRUCT {{
                    <http://dbpedia.org/resource/{artist_name_for_request}> foaf:name ?name ;
                        dbo:activeYearsStartYear ?activeYearsStartYear ;
                        dbo:birthDate ?birthDate ;
                        dbo:birthPlace ?birthPlace ;
                        dbo:genre ?genre ;
                        dbo:hometown ?hometown .
                }}
                WHERE {{
                    OPTIONAL {{ <http://dbpedia.org/resource/{artist_name_for_request}> foaf:name ?name . }}
                    OPTIONAL {{ <http://dbpedia.org/resource/{artist_name_for_request}> dbo:activeYearsStartYear ?activeYearsStartYear . }}
                    OPTIONAL {{ <http://dbpedia.org/resource/{artist_name_for_request}> dbo:birthDate ?birthDate . }}
                    OPTIONAL {{ <http://dbpedia.org/resource/{artist_name_for_request}> dbo:birthPlace ?birthPlace . }}
                    OPTIONAL {{ <http://dbpedia.org/resource/{artist_name_for_request}> dbo:genre ?genre . }}
                    OPTIONAL {{ <http://dbpedia.org/resource/{artist_name_for_request}> dbo:hometown ?hometown . }}
                }}
                """

        select_query = f"""
                PREFIX dbo: <http://dbpedia.org/ontology/>
                PREFIX foaf: <http://xmlns.com/foaf/0.1/>

                SELECT ?name ?activeYearsStartYear ?birthDate ?birthPlace (GROUP_CONCAT(?genre; separator=", ") AS ?genres) ?hometown
                WHERE {{
                    OPTIONAL {{ <http://dbpedia.org/resource/{artist_name_for_request}> foaf:name ?name . }}
                    OPTIONAL {{ <http://dbpedia.org/resource/{artist_name_for_request}> dbo:activeYearsStartYear ?activeYearsStartYear . }}
                    OPTIONAL {{ <http://dbpedia.org/resource/{artist_name_for_request}> dbo:birthDate ?birthDate . }}
                    OPTIONAL {{ <http://dbpedia.org/resource/{artist_name_for_request}> dbo:birthPlace ?birthPlace . }}
                    OPTIONAL {{ <http://dbpedia.org/resource/{artist_name_for_request}> dbo:genre ?genre . }}
                    OPTIONAL {{ <http://dbpedia.org/resource/{artist_name_for_request}> dbo:hometown ?hometown . }}
                }}
                GROUP BY ?name ?activeYearsStartYear ?birthDate ?birthPlace ?hometown
                """

        response_construct = requests.get(
            dbpedia_endpoint, params={'query': construct_query, 'format': 'text/turtle'}
        )
        response_select = requests.get(
            dbpedia_endpoint, params={'query': select_query, 'format': 'application/sparql-results+json'}
        )

        construct_result = rdflib.Graph()
        select_result = None

        if response_construct.status_code == 200:
            construct_result.parse(data=response_construct.text, format="turtle")

        if response_select.status_code == 200:
            select_result = response_select.json()

        return construct_result, select_result

    def getArtist(self, filter_var: str, filter_value: str):
        """
        Generic method to fetch artist details from both the internal database and DBpedia,
        merging the graphs using the artist name with owl:sameAs or an equivalent.

        :param filter_var: The variable to filter on (e.g., "artistName", "artistSpotifyURI").
        :param filter_value: The value to filter by.
        :return: A tuple of (merged_construct_result, merged_select_result).
        """
        construct_query = f"""
        PREFIX media: <http://mediafinder.org/media/>
        PREFIX property: <http://mediafinder.org/properties/>

        CONSTRUCT {{
            ?artist a media:Artist .
            ?artist property:artistName ?artistName .
            ?artist property:artistSpotifyURI ?artistSpotifyURI .
        }}
        WHERE {{
            ?artist a media:Artist .
            ?artist property:artistName ?artistName .
            ?artist property:artistSpotifyURI ?artistSpotifyURI .
            FILTER (regex(str(?{filter_var}), "{filter_value}", "i"))
        }}
        """

        select_query = f"""
        PREFIX media: <http://mediafinder.org/media/>
        PREFIX property: <http://mediafinder.org/properties/>

        SELECT ?artist ?artistName ?artistSpotifyURI
        WHERE {{
            ?artist a media:Artist .
            ?artist property:artistName ?artistName .
            ?artist property:artistSpotifyURI ?artistSpotifyURI .
            FILTER (regex(str(?{filter_var}), "{filter_value}", "i"))
        }}
        """

        self.sparql.setQuery(construct_query)
        self.sparql.setReturnFormat(JSON)
        internal_construct_result = rdflib.Graph()
        internal_construct_result.parse(data=self.sparql.query().response.read(), format="json-ld")

        self.sparql.setQuery(select_query)
        self.sparql.setReturnFormat(JSON)
        internal_select_result = self.sparql.query().convert()

        if len(internal_select_result["results"]["bindings"]) == 0:
            return internal_construct_result, internal_select_result

        artist_name = internal_select_result['results']['bindings'][0]['artistName']['value']

        dbpedia_construct_result, dbpedia_select_result = self._getDbpediaArtistInfo(artist_name)

        merged_construct_result = internal_construct_result + dbpedia_construct_result
        merged_select_result = internal_select_result

        if dbpedia_select_result and "results" in dbpedia_select_result and "bindings" in dbpedia_select_result[
            "results"]:
            dbpedia_binding = dbpedia_select_result["results"]["bindings"][0]

            dbpedia_vars = dbpedia_select_result["head"]["vars"]
            for var in dbpedia_vars:
                if var not in merged_select_result["head"]["vars"]:
                    if var != "name":
                        merged_select_result["head"]["vars"].append(var)

            for internal_binding in merged_select_result["results"]["bindings"]:
                for key, value in dbpedia_binding.items():
                    if key not in internal_binding:
                        internal_binding[key] = value
                    elif isinstance(internal_binding[key], list):
                        if value not in internal_binding[key]:
                            internal_binding[key].append(value)
                    else:
                        if internal_binding[key] != value:
                            internal_binding[key] = [internal_binding[key], value]

        return merged_construct_result, merged_select_result

    """
        Methods to get tracks
    """

    def getTrackByName(self, track_name):
        return self.getTracks("trackName", track_name)

    def getTrackByArtistName(self, artist_name):
        return self.getTracks("artistName", artist_name)

    def getTrackByAlbumName(self, album_name):
        return self.getTracks("albumName", album_name)

    def getTrackByURI(self, track_uri):
        return self.getTracks("track", track_uri)

    def getTrackByAlbumURI(self, album_uri):
        return self.getTracks("album", album_uri)

    def getTrackBySpotifyURI(self, spotify_uri):
        return self.getTracks("trackSpotifyURI", spotify_uri)

    def getTrackByISRC(self, isrc):
        return self.getTracks("trackISRC", isrc)

    """
        Methods to get albums
    """

    def getAlbumByName(self, album_name):
        return self.getAlbum("albumName", album_name)

    def getAlbumByURI(self, album_uri):
        return self.getAlbum("album", album_uri)

    def getAlbumBySpotifyURI(self, album_spotify_uri):
        return self.getAlbum("albumSpotifyURI", album_spotify_uri)

    def getAlbumByType(self, album_type):
        return self.getAlbum("albumType", album_type)

    """
        Methods to get artists
    """

    def getArtistByName(self, artist_name):
        return self.getArtist("artistName", artist_name)

    def getArtistByURI(self, artist_uri):
        return self.getArtist("artist", artist_uri)

    def getArtistBySpotifyURI(self, artist_spotify_uri):
        return self.getArtist("artistSpotifyURI", artist_spotify_uri)
