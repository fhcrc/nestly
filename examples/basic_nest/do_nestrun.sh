nestrun --processes 2 --template-file echo.sh $(find runs -name control.json)
nestagg delim $(find runs -name "log.txt") -o aggregate.csv
