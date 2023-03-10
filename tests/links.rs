use mystuff::datastore::memory::MemoryDataStore;
use mystuff::datastore::DataStore;
use mystuff::links::add_link;

#[test]
fn should_add_link() {
    let datastore = MemoryDataStore::new();

    let new_url = String::from("http://www.example.com");

    add_link(
        datastore,
        new_url.clone(),
        Vec::new(),
        Some(String::from("description")),
    );

    let links = datastore.get_links();

    assert!(links.contains_key(&new_url));
}
