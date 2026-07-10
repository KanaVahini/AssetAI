"""
Master pipeline script that runs the following steps in order:
1. ingest
2. extract_entities
3. build_graph
4. build_vector_store
"""

def run_pipeline():
    print("Starting pipeline: ingest")
    # placeholder: call ingestion
    print("Finished ingest")

    print("Starting pipeline: extract_entities")
    # placeholder: call entity extraction
    print("Finished extract_entities")

    print("Starting pipeline: build_graph")
    # placeholder: build knowledge graph
    print("Finished build_graph")

    print("Starting pipeline: build_vector_store")
    # placeholder: build vector store
    print("Finished build_vector_store")


if __name__ == '__main__':
    run_pipeline()
