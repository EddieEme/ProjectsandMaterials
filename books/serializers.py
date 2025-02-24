from rest_framework import serializers
from .models import BookType, Category, Book

class BookTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookType
        fields = ['id', 'name']  # Serialize all fields in the BookType model

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class BookSerializer(serializers.ModelSerializer):
    # Include related fields for book_type and category
    book_type = BookTypeSerializer(read_only=True)
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Book
        fields = '__all__'  # Serialize all fields in the Book model