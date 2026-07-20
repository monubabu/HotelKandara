from django.db import models

# Create your models here.
class Amenity(models.Model):
      name = models.CharField(max_length=100, unique=True)
      icon_name = models.CharField(max_length=50,blank = True,null=True,help_text="CSS/FontAwesome icon class for frontend use")


      class Meta:
            verbose_name_plural = "Amenities"

      def __str__(self):
            return self.name
      
class RoomType(models.Model):
            name = models.CharField(max_length=100,unique=True)
            description = models.TextField()
            price_per_night = models.DecimalField(max_digits=10,decimal_places=2)
            max_capacity = models.PositiveIntegerField(default=2)
            amenities = models.ManyToManyField(Amenity, related_name="room_types",blank=True)
            image = models.ImageField(upload_to="room_types/",blank=True,null = True)

            def __str__(self):
                  return self.name

class Room(models.Model):
       STATUS_CHOICE = (
              ('available','Available'),
              ('occupied','Occupied'),
              ('cleaning','Under Cleaning'),
              ('maintenance','Maintenance'),
       )

       room_number = models.CharField(max_length=50,unique = True) # for eg: 101,102,HALL
       room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT,related_name="rooms")
       floor = models.PositiveIntegerField(default=1)
       status = models.CharField(max_length=20, choices=STATUS_CHOICE,default = 'available')

       def __str__(self):
              return f"Room {self.room_number} ({self.room_type.name})"
       
            



