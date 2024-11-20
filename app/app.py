import streamlit as st
from media_finder import MediaFinder
from rdflib import Graph
from pyvis.network import Network
from PIL import Image
import base64
import io

media_finder = MediaFinder("http://localhost:3030/media-finder/")

st.set_page_config(page_title="Media Finder", layout="wide")
st.title("🎵 Media Finder")

st.sidebar.header("Search Options")

media_type = st.sidebar.selectbox(
    "Choose Media Type",
    ["Select Media", "Music", "Image"],
    index=0
)

search_criteria = None
search_method = None

if media_type == "Music":
    search_criteria = st.sidebar.selectbox(
        "Search For",
        ["Select Criteria", "Track", "Album", "Artist"],
        index=0
    )

    if search_criteria == "Track":
        search_method = st.sidebar.selectbox(
            "Filter By",
            ["Select Criteria", "Name", "ISRC", "URI", "Spotify URI", "Artist Name", "Album Name", "Album URI"],
            index=0
        )
    elif search_criteria == "Album":
        search_method = st.sidebar.selectbox(
            "Filter By",
            ["Select Criteria", "Name", "URI", "Spotify URI", "Type"],
            index=0
        )
    elif search_criteria == "Artist":
        search_method = st.sidebar.selectbox(
            "Filter By",
            ["Select Criteria", "Name", "URI", "Spotify URI"],
            index=0
        )

    if search_criteria != "Select Criteria" and search_method != "Select Criteria":
        if search_criteria == "Track":
            st.subheader("Search for Music Tracks")

            if search_method == "Name":
                search_input = st.text_input("Enter Track Name", "")
                search_function = media_finder.getTrackByName
            elif search_method == "ISRC":
                search_input = st.text_input("Enter Track ISRC", "")
                search_function = media_finder.getTrackByISRC
            elif search_method == "URI":
                search_input = st.text_input("Enter Track URI", "")
                search_function = media_finder.getTrackByURI
            elif search_method == "Spotify URI":
                search_input = st.text_input("Enter Spotify URI", "")
                search_function = media_finder.getTrackBySpotifyURI
            elif search_method == "Artist Name":
                search_input = st.text_input("Enter Artist Name", "")
                search_function = media_finder.getTrackByArtistName
            elif search_method == "Album Name":
                search_input = st.text_input("Enter Album Name", "")
                search_function = media_finder.getTrackByAlbumName
            elif search_method == "Album URI":
                search_input = st.text_input("Enter Album URI", "")
                search_function = media_finder.getTrackByAlbumURI
            else:
                search_input = ""
                search_function = None

        elif search_criteria == "Album":
            st.subheader("Search for Music Albums")

            if search_method == "Name":
                search_input = st.text_input("Enter Album Name", "")
                search_function = media_finder.getAlbumByName
            elif search_method == "URI":
                search_input = st.text_input("Enter Album URI", "")
                search_function = media_finder.getAlbumByURI
            elif search_method == "Spotify URI":
                search_input = st.text_input("Enter Album Spotify URI", "")
                search_function = media_finder.getAlbumBySpotifyURI
            elif search_method == "Type":
                search_input = st.text_input("Enter Album Type", "")
                search_function = media_finder.getAlbumByType
            else:
                search_input = ""
                search_function = None

        elif search_criteria == "Artist":
            st.subheader("Search for Music Artists")

            if search_method == "Name":
                search_input = st.text_input("Enter Artist Name", "")
                search_function = media_finder.getArtistByName
            elif search_method == "URI":
                search_input = st.text_input("Enter Artist URI", "")
                search_function = media_finder.getArtistByURI
            elif search_method == "Spotify URI":
                search_input = st.text_input("Enter Artist Spotify URI", "")
                search_function = media_finder.getArtistBySpotifyURI
            else:
                search_input = ""
                search_function = None

        if st.button("Search"):
            if search_input.strip() and search_function:
                construct_result, select_result = search_function(search_input)

                result_list = list(select_result["results"]["bindings"])

                if len(result_list) > 0:
                    st.success(f"### {len(result_list)} result(s) found")
                else:
                    st.warning("No results found for your search.")

                if len(result_list) > 0:
                    st.write("### Visualizing the Results")

                    mini_graph = Graph()
                    mini_graph += construct_result

                    net = Network(notebook=False, height="600px", width="100%")
                    for subj, pred, obj in mini_graph:
                        net.add_node(str(subj), label=str(subj), color="skyblue")
                        net.add_node(str(obj), label=str(obj), color="lightgreen")
                        net.add_edge(str(subj), str(obj), title=str(pred.split('/')[-1]),
                                     label=str(pred.split('/')[-1]))

                    graph_file = "rdf_graph_result.html"
                    net.write_html(graph_file)
                    st.components.v1.html(open(graph_file, 'r').read(), height=600)

                    st.write("### Tabular Results")

                    column_names = select_result["head"]["vars"]

                    table_data = [
                        {col: row.get(col, {}).get("value", "N/A") for col in column_names}
                        for row in select_result["results"]["bindings"]
                    ]

                    st.table(table_data)

            else:
                st.error("Please enter a valid input to search.")
    else:
        st.info("Please choose search criteria and method to proceed with the search.")

elif media_type == "Image":

    option = st.sidebar.selectbox("Choose Option", ["Select Option", "Insert", "Search"], index=0)

    if option == "Insert":
        st.subheader("Upload an Image for Object Detection")
        uploaded_file = st.file_uploader("Upload an image", type=["jpg", "png", "jpeg"])

        if uploaded_file is not None:
            col1, col2 = st.columns(2)

            with col1:
                image = Image.open(uploaded_file)
                st.image(image, caption="Uploaded Image", use_container_width=False, width=425)

            with col2:
                result_image, detected_objects = media_finder.detect_objects(image)
                st.image(result_image, caption="Processed Image with Object Detection", use_container_width=False,
                         width=425)

            if st.button("Save"):
                media_finder.save_image_to_triplestore(result_image, detected_objects)
                st.success("Image and objects saved successfully!")

    elif option == "Search":

        search_term = st.text_input("Search for an image containing an object (e.g., 'cat', 'dog', etc.)")

        if st.button("Search"):
            if search_term:
                results = media_finder.search_for_images(search_term)
                if results["results"]["bindings"]:
                    st.write(f"Found {len(results['results']['bindings'])} result(s)")
                    for result in results["results"]["bindings"]:
                        image_base64 = result['base64Value']['value']
                        image_data = base64.b64decode(image_base64)
                        image = Image.open(io.BytesIO(image_data))
                        st.image(image, caption=result['image']['value'], use_container_width=False,
                                 width=350)
                else:
                    st.warning(f"No images found containing the object '{search_term}'.")

else:
    st.info("Please choose a media type.")
