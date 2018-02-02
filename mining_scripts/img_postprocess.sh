RESDIR=../res
DIR=$RESDIR/imgs_table_horiz
rm -rf $DIR
mkdir $DIR
for a in $RESDIR/imgs/*; do
    gm convert -resize x200 -rotate 90 $a $DIR/$(basename $a)
done
