use serde::{Deserialize, Serialize};
use serde_json::json;
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, BufRead};
use std::path::{Path, PathBuf};

#[derive(Clone, Debug, Deserialize, Serialize)]
struct Link {
    url: String,
    description: String,
    tags: Vec<String>,
}

impl Link {
    fn new(url: &String, description: String, tags: String) -> Link {
        let cleaned_tags = tags
            .split(",")
            .map(|tag| String::from(tag.trim()))
            .collect();
        Link {
            url: url.clone(),
            description,
            tags: cleaned_tags,
        }
    }
}

fn read_links_to_map(filename: &PathBuf) -> HashMap<String, Link> {
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

fn write_links_to_file(links: Vec<String>, filename: &PathBuf) {
    std::fs::write(filename, links.join("\n")).expect("failed to write to file");
}

pub fn handle_link(data: String, add: Option<String>, verbose: bool) {
    let links_file = Path::new(&data).join("links.jsonl");
    if !links_file.clone().exists() {
        File::create(links_file.clone()).unwrap_or_else(|error| {
            panic!("Problem creating the file: {:?}", error);
        });
    }

    // read json file and group into a map by url
    let mut links = read_links_to_map(&links_file);

    if add.is_some() {
        let url = add.unwrap();
        let link = Link::new(
            &url,
            String::from("this is a description"),
            String::from("1, 2, 3, 4"),
        );

        if !links.contains_key(&url) {
            let json_link = json!(link.clone());

            if verbose {
                println!("==> Added link {json_link:#}");
            }

            links.insert(link.url.clone(), link.clone());

            let updated_links: Vec<String> = links
                .values()
                .map(|obj| serde_json::to_string(obj).unwrap())
                .collect();

            write_links_to_file(updated_links, &links_file);
        } else {
            println!("Link {url} already exists");
        }
    } else {
        for (link, obj) in links {
            println!("{:?} - {:?}", link, obj.clone())
        }
    }
}
