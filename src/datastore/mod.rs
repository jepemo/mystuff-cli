mod local;

use crate::types::Link;
use std::collections::HashMap;

trait DataStore {
    fn get_links(&self) -> HashMap<String, Link>;
    fn set_links(&self, links: &HashMap<String, Link>);
}
