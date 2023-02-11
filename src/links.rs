use serde::{Deserialize, Serialize};
use serde_json::json;
use std::fs::File;
// use std::fs::OpenOptions;
use std::path::Path;

#[derive(Serialize, Deserialize)]
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

pub fn handle_link(data: String, add: Option<String>) {
    let links_file = Path::new(&data).join("links.jsonl");
    if !links_file.exists() {
        File::create(links_file).unwrap_or_else(|error| {
            panic!("Problem creating the file: {:?}", error);
        });
    }

    if add.is_some() {
        let url = add.unwrap();
        let link = Link::new(
            url,
            String::from("this is a description"),
            String::from("1, 2, 3, 4"),
        );

        // read json file and group into a map by url

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
        println!("Show list")
    }

    // let paths = fs::read_dir(default_path.as_ref()).unwrap();
    // for path in paths {
    //     println!("Name: {}", path.unwrap().path().display())
    // }
}
