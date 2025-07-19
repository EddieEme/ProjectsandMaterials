from rest_framework import serializers
from .models import BookType, Category, Book

class BookTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookType
        fields = '__all__'  

class CategorySerializer(serializers.ModelSerializer):
    book_type = BookTypeSerializer(read_only=True) 

    class Meta:
        model = Category
        fields = '__all__'

class BookSerializer(serializers.ModelSerializer):
    book_type = BookTypeSerializer(read_only=True) 
    category = CategorySerializer(read_only=True)
    user = serializers.StringRelatedField(read_only=True)
    file_statistics = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = '__all__' 

    def get_file_statistics(self, obj):
        return obj.get_file_statistics()
