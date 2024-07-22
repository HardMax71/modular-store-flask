1. Extract messages from the source code

```shell
pybabel extract -F ../translations/babel.cfg -k _l -o ../translations/messages.pot .
```

2. Create a new language catalog
```shell
pybabel init -i translations/messages.pot -d translations -l ru
```

> If catalog exists, use `pybabel update -i translations/messages.pot -d translations -l ru`

3. Compile the language catalog => for usage in the app
```shell
pybabel compile -d translations
```

3.1. If compile all, including fuzzy translations
```shell
 pybabel compile -f -d translations
```

4. Update the language catalog
```shell
pybabel update -i translations/messages.pot -d translations -l ru
```

Further hints: https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xiii-i18n-and-l10n
