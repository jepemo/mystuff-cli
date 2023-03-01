use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Link {
    pub url: String,
    pub description: String,
    pub tags: Vec<String>,
}
