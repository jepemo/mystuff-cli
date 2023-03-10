use super::DataStore;
use crate::types::Link;
use std::collections::HashMap;

pub struct MemoryDataStore {
    pub links: HashMap<String, Link>,
}

impl MemoryDataStore {
    pub fn new() -> Self {
        MemoryDataStore {
            links: HashMap::new(),
        }
    }
}

impl DataStore for MemoryDataStore {
    fn get_links(&self) -> HashMap<String, Link> {
        self.links.clone()
    }

    fn set_links(&mut self, links: &HashMap<String, Link>) {
        self.links = links.clone()
    }
}
