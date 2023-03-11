use mystuff::datastore::memory::MemoryDataStore;
use mystuff::datastore::DataStore;
use mystuff::links::add_link;

#[test]
fn should_add_link() {
    let mut datastore = MemoryDataStore::new();

    let new_url = String::from("http://www.example.com");

    add_link(
        &mut datastore,
        new_url.clone(),
        vec![String::from("t1"), String::from("t2")],
        Some(String::from("description")),
    );

    let links = datastore.get_links();

    assert!(links.contains_key(&new_url));
}
