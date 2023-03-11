use mystuff::datastore::memory::MemoryDataStore;
use mystuff::datastore::DataStore;
use mystuff::links::add_link;

#[test]
fn should_create_a_link() {
    let new_url = String::from("http://www.example.com");
    let new_description = String::from("description");
    let new_tags = vec![String::from("tag1"), String::from("tag2")];

    let created_link = add_link(
        &mut MemoryDataStore::new(),
        new_url.clone(),
        new_tags.clone(),
        Some(new_description.clone()),
    );

    assert_eq!(created_link.url, new_url);
    assert_eq!(created_link.description, new_description);

    for tag in new_tags {
        assert!(created_link.tags.contains(&tag.clone()));
    }
}

#[test]
fn should_store_link_in_datastore() {
    let mut datastore = MemoryDataStore::new();

    let new_url = String::from("http://www.example.com");
    let new_description = String::from("description");
    let new_tags = vec![String::from("tag1"), String::from("tag2")];

    add_link(
        &mut datastore,
        new_url.clone(),
        new_tags.clone(),
        Some(new_description.clone()),
    );

    let links = datastore.get_links();

    assert!(links.contains_key(&new_url));

    let stored_url = links.get(&new_url).unwrap();
    assert_eq!(stored_url.url, new_url);
    assert_eq!(stored_url.description, new_description);

    for tag in new_tags {
        assert!(stored_url.tags.contains(&tag.clone()));
    }
}

#[test]
fn should_return_an_existing_link_because_already_exists() {
    let mut datastore = MemoryDataStore::new();

    let new_url = String::from("http://www.example.com");
    let new_description = String::from("description");
    let new_tags = vec![String::from("tag1"), String::from("tag2")];

    add_link(
        &mut datastore,
        new_url.clone(),
        new_tags.clone(),
        Some(new_description.clone()),
    );

    let existing_link = add_link(
        &mut datastore,
        new_url.clone(),
        new_tags.clone(),
        Some(new_description.clone()),
    );

    assert_eq!(existing_link.url, new_url);
    assert_eq!(existing_link.description, new_description);

    for tag in new_tags {
        assert!(existing_link.tags.contains(&tag.clone()));
    }
}
