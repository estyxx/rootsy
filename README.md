# Rootsy

Rootsy is a modern Python package for parsing GEDCOM files. GEDCOM is a standard file format for genealogical data, and Rootsy makes it easy to work with this data in Python.

## Features

- Parse GEDCOM files into Python objects
- Navigate and manipulate genealogical data
- Support for GEDCOM 5.5 and 5.5.1 standards

## Installation

You can install Rootsy using pip:

```bash
pip install rootsy
```

## Usage

Here's a simple example of how to use Rootsy to parse a GEDCOM file:

```python
import rootsy

# Load a GEDCOM file
gedcom_file = 'path/to/your/file.ged'
parser = rootsy.GedcomParser()
tree = parser.parse(gedcom_file)

# Access individuals
for individual in tree.individuals:
    print(individual.name)
```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on GitHub.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

For any questions or suggestions, please open an issue on GitHub.
