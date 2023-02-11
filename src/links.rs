use std::fs::File;
use std::path::Path;

pub fn handle_link(data: String, add: Option<String>) {
    let links_file = Path::new(&data).join("links.jsonl");
    if !links_file.exists() {
        File::create(links_file).unwrap_or_else(|error| {
            panic!("Problem creating the file: {:?}", error);
        });
    }

    if add.is_some() {
        println!("Add link {:?}", add.unwrap())
    } else {
        println!("Show list")
    }

    // let paths = fs::read_dir(default_path.as_ref()).unwrap();
    // for path in paths {
    //     println!("Name: {}", path.unwrap().path().display())
    // }
}
