use std::collections::HashMap;
use std::fs::File;
use std::io::{self, BufRead};
use std::path::{Path, PathBuf};

use super::DataStore;
use crate::types::Link;

struct LocalDataStore {
    path: PathBuf,
}

impl DataStore for LocalDataStore {
    fn get_links(&self) -> HashMap<String, Link> {
        let filename = Path::new(&self.path).join("links.jsonl");
        let file = File::open(filename).unwrap();
        let lines = io::BufReader::new(file).lines();

        lines
            .map(|line| {
                let data = line.unwrap();
                let obj: Link = serde_json::from_str(&data).unwrap();
                (obj.url.clone(), obj)
            })
            .collect()
    }

    fn set_links(&self, links: &HashMap<String, Link>) {
        let filename = Path::new(&self.path).join("links.jsonl");

        let updated_links: Vec<String> = links
            .values()
            .map(|obj| serde_json::to_string(obj).unwrap())
            .collect();

        std::fs::write(filename, updated_links.join("\n")).expect("failed to write to file");
    }
}
