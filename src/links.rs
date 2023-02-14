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
    fn new(url: String, description: String, tags: String) -> Link {
        let cleaned_tags = tags
            .split(",")
            .map(|tag| String::from(tag.trim()))
            .collect();
        Link {
            url,
            description,
            tags: cleaned_tags,
        }
    }
}

fn read_links_to_map(filename: PathBuf) -> HashMap<String, Link> {
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

pub fn handle_link(data: String, add: Option<String>) {
    let links_file = Path::new(&data).join("links.jsonl");
    if !links_file.clone().exists() {
        File::create(links_file.clone()).unwrap_or_else(|error| {
            panic!("Problem creating the file: {:?}", error);
        });
    }

    // read json file and group into a map by url
    let links = read_links_to_map(links_file);

    if add.is_some() {
        let url = add.unwrap();
        let link = Link::new(
            url,
            String::from("this is a description"),
            String::from("1, 2, 3, 4"),
        );

        // check if the url exist
        // -> show a meesage and exit if exists

        // add the new link in the map

        // append the link in the file
        // or?
        // write again the map in the file
        let json_link = json!(link);
        println!("Add link {:?}", json_link);

        // let mut file = OpenOptions::new().append(true).open(links_file).unwrap();

        // if let Err(e) = writeln!(file, "{}", json_link) {
        //     eprintln!("Couldn't write to file: {}", e);
        // }
    } else {
        for (link, obj) in links {
            println!("{:?} - {:?}", link, obj.clone())
        }
    }

    // let paths = fs::read_dir(default_path.as_ref()).unwrap();
    // for path in paths {
    //     println!("Name: {}", path.unwrap().path().display())
    // }
}
