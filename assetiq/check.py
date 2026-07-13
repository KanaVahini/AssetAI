import json

with open('data/processed/cleaned_documents.jsonl') as f:
    docs = [json.loads(line) for line in f]

print(f'Total docs: {len(docs)}')
for doc in docs:
    print(f"{doc['filename']} → {len(doc['entities'])} entities")