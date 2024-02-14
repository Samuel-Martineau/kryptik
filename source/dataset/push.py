from datasets import load_dataset, concatenate_datasets, DatasetDict

old = load_dataset("Samuel-Martineau/kryptik")
new = load_dataset("imagefolder", data_dir="./tmp/dataset")

combined = DatasetDict({
    key: concatenate_datasets([
        d for d in
        [old.get(key, None), new.get(key, None)]
        if d is not None
    ])
    for key in set(new.keys()) | set(old.keys())
})

combined.push_to_hub("Samuel-Martineau/kryptik")
