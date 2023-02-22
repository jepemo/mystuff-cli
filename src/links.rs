use inquire::{
    autocompletion::{Autocomplete, Replacement},
    CustomUserError, Text,
};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::collections::{HashMap, HashSet};
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

#[derive(Clone, Default)]
struct TagCompleter {
    tags: Vec<String>,
    input: String,
}

impl Autocomplete for TagCompleter {
    fn get_suggestions(&mut self, input: &str) -> Result<Vec<String>, CustomUserError> {
        let val_lower = input.trim().to_lowercase();
        if "".eq(&val_lower) {
            return Ok(Vec::new());
        }

        let current_tag = val_lower
            .split(", ")
            .map(|word| word.trim())
            .last()
            .unwrap();

        self.input = String::from(input);

        Ok(self
            .tags
            .iter()
            .filter(|s| s.to_lowercase().contains(&current_tag))
            .map(|s| String::from(s.clone()))
            .collect())
    }

    fn get_completion(
        &mut self,
        _: &str,
        suggestion: Option<String>,
    ) -> Result<Replacement, CustomUserError> {
        let new_input = match self.input.rfind(",") {
            None => String::from(""),
            Some(idx) => format!("{}, ", &self.input.clone()[0..idx]),
        };

        match suggestion {
            None => Ok(Some(new_input)),
            Some(sug) => {
                return Ok(Some(format!("{}{}", new_input, sug)));
            }
        }
    }
}

fn read_link_data_from_prompt(url: &String, tags: &Vec<String>) -> Link {
    let link = Link::new(
        &url,
        Text::new("Description").prompt().unwrap(),
        Text::new("Tags (t1,t2,t3):")
            .with_autocomplete(TagCompleter {
                input: String::from(""),
                tags: tags.clone(),
            })
            .prompt()
            .unwrap(),
    );

    link
}

fn get_tags_from_links(links: &HashMap<String, Link>) -> Vec<String> {
    let tags: HashSet<_> = links
        .values()
        .into_iter()
        .flat_map(|link| link.tags.clone())
        .map(|tag| String::from(tag.to_lowercase().trim()))
        .collect();

    tags.into_iter().collect::<Vec<String>>()
}

pub fn handle_link(data: String, add: Option<String>, verbose: bool) {
    let links_file = Path::new(&data).join("links.jsonl");
    if !links_file.clone().exists() {
        File::create(links_file.clone()).unwrap_or_else(|error| {
            panic!("Problem creating the file: {:?}", error);
        });
    }

    let mut links = read_links_to_map(&links_file);

    if add.is_some() {
        let url = add.unwrap();
        let tags = get_tags_from_links(&links);

        if !links.contains_key(&url) {
            let link = read_link_data_from_prompt(&url, &tags);
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
