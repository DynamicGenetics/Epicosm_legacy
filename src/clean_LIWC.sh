# LIWC cannot deal with the 22 categories listed below
# ... this script removes them.

if [ $# -eq 0 ]; then
    echo "Please provide a dictionary to clean."
    echo "Example:"
    echo "bash clean_LIWC.sh LIWC2015_dictionary.dic"
    exit 1
fi

cp "$1" "$1".clean
sed -ie "/) like/d" "$1".clean
sed -ie "/to like/d" "$1".clean
sed -ie "/kind of/d" "$1".clean

echo "OK, $1 cleaned, output dictionary is $1.clean"

#kind of    50    54
#to like 20      30      31      91
#(i) like*       20      30      31
#(you) like*     20      30      31
#(we) like*      20      30      31
#(they) like*    20      30      31
#(do) like       30      31
#(don't) like    30      31
#(did) like      30      31
#(didn't) like   30      31
#(will) like     30      31
#(won't) like    30      31
#(does) like     30      31
#(doesn't) like  30      31
#(did not) like  30      31
#(will not) like 30      31
#(do not) like   30      31
#(does not) like 30      31
#(would not) like        30      31
#(should not) like       30      31
#(could not) like        30      31
#(53) like*      30      31