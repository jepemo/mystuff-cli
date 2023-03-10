pub mod local;
pub mod memory;

use crate::types::Link;
use std::collections::HashMap;

pub trait DataStore {
    fn get_links(&self) -> HashMap<String, Link>;
    fn set_links(&mut self, links: &HashMap<String, Link>);
}
