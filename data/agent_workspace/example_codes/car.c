#include <stdio.h>
#include <string.h>

// Define the Car structure
struct Car {
    char make[50];
    char model[50];
    int year;
    float price;
    int mileage;
};

// Function to display car information
void displayCar(struct Car car) {
    printf("Car Details:\n");
    printf("Make: %s\n", car.make);
    printf("Model: %s\n", car.model);
    printf("Year: %d\n", car.year);
    printf("Price: $%.2f\n", car.price);
    printf("Mileage: %d miles\n", car.mileage);
    printf("\n");
}

// Function to create a car
struct Car createCar(char* make, char* model, int year, float price, int mileage) {
    struct Car newCar;
    strcpy(newCar.make, make);
    strcpy(newCar.model, model);
    newCar.year = year;
    newCar.price = price;
    newCar.mileage = mileage;
    return newCar;
}

int main() {
    // Create car objects using different methods
    
    // Method 1: Direct initialization
    struct Car car1 = {"Toyota", "Camry", 2022, 25000.00, 15000};
    
    // Method 2: Member-by-member assignment
    struct Car car2;
    strcpy(car2.make, "Honda");
    strcpy(car2.model, "Civic");
    car2.year = 2021;
    car2.price = 22000.00;
    car2.mileage = 20000;
    
    // Method 3: Using a function
    struct Car car3 = createCar("Ford", "Mustang", 2023, 35000.00, 5000);
    
    // Display all cars
    printf("=== Car Inventory ===\n\n");
    displayCar(car1);
    displayCar(car2);
    displayCar(car3);
    
    return 0;
}