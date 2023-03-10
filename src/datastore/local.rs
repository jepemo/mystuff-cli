use std::collections::HashMap;
use std::fs;
use std::fs::File;
use std::io::{self, BufRead};
use std::path::{Path, PathBuf};

use super::DataStore;
use crate::types::Link;

pub struct LocalDataStore {
    pub path: PathBuf,
}

impl LocalDataStore {
    pub fn new(arg_data: Option<String>) -> Self {
        let default_path = shellexpand::tilde("~/.mystuff");
        let data = arg_data
            .clone()
            .unwrap_or_else(|| String::from(default_path.clone()));

        if !Path::new(&data).is_dir() {
            match fs::create_dir(&data) {
                Ok(_file) => {
                    log::info!("==> creating directory {}", &data)
                }
                Err(error) => {
                    panic!("cannot create directory; {}, error: {:?}", &data, error);
                }
            }
        }

        // Check links
        let links_filepath = Path::new(&data).join("links.jsonl");
        if !links_filepath.exists() {
            File::create(links_filepath).unwrap();
        }

        LocalDataStore {
            path: PathBuf::from(data),
        }
    }
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

    fn set_links(&mut self, links: &HashMap<String, Link>) {
        let filename = Path::new(&self.path).join("links.jsonl");

        let updated_links: Vec<String> = links
            .values()
            .map(|obj| serde_json::to_string(obj).unwrap())
            .collect();

        std::fs::write(filename, updated_links.join("\n")).expect("failed to write to file");
    }
}
