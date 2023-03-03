use inquire::{
    autocompletion::{Autocomplete, Replacement},
    CustomUserError, Text,
};

use crate::datastore::DataStore;
use crate::types::Link;
use serde_json::json;
use std::collections::{HashMap, HashSet};

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

pub fn add_link<T: DataStore>(datastore: T, url: String) {
    let mut links = datastore.get_links();
    let tags = get_tags_from_links(&links);

    if !links.contains_key(&url) {
        let link = read_link_data_from_prompt(&url, &tags);

        log::info!("==> Added link {:#}", json!(link.clone()));

        links.insert(link.url.clone(), link.clone());

        datastore.set_links(&links);
    } else {
        println!("Link {url} already exists");
    }
}

pub fn list_links<T: DataStore>(datastore: T) {
    let links = datastore.get_links();
    for (link, obj) in links {
        println!("{:?} - {:?}", link, obj.clone())
    }
}
