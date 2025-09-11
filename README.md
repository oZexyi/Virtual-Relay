---
title: Virtual Relay System
sdk: gradio
app_file: app.py
---

# Virtual Relay System

A comprehensive automated shipping relay management system for Flowers Foods operations, featuring interactive trailer management, real-time dispatch tracking, and intelligent order processing.

## 🚛 System Overview

The Virtual Relay System is a complete logistics management platform that automates the creation and management of shipping relays across multiple locations. The system processes orders, calculates optimal trailer assignments, and provides real-time tracking of trailer dispatch status.

### Core Components

- **Order Management System**: Automated order creation and processing across 135+ routes
- **Interactive Relay Display**: Visual, clickable trailer management interface
- **Real-time Dispatch Tracking**: Live status updates with color-coded trailer states
- **Product-Specific Calculations**: Intelligent stack height calculations based on product types
- **Date-based Operations**: North Carolina timezone integration with flexible scheduling

## ✨ Key Features

### 📋 Order Management
- **Automated Order Generation**: Creates realistic orders for all 135 routes with configurable parameters
- **Product Integration**: Loads 252+ products with specific stack heights and tray configurations
- **Route Management**: Supports 16+ locations with multiple routes per location
- **Date & Day Selection**: Flexible scheduling with Day 1-6 operations

### 🎯 Interactive Relay System
- **Visual Trailer Cards**: Color-coded trailer displays with real-time status updates
- **Click-to-Edit Interface**: Direct trailer editing through visual identifier system
- **Live Status Updates**: Red (Active) and Green (Dispatched) color coding
- **Comprehensive Information**: LD numbers, stack counts, seal numbers, and trailer numbers

### 🚀 Advanced Functionality
- **Real-time API Integration**: North Carolina timezone synchronization via WorldTimeAPI
- **Persistent State Management**: File-based state tracking for reliable operations
- **Multi-trailer Support**: Intelligent trailer allocation with 98-stack capacity limits
- **Dispatch Management**: Permanent trailer finalization with confirmation workflows

## 🎮 User Interface

### System Overview Tab
- Complete system documentation and feature overview
- Professional presentation for stakeholders and users

### Orders Tab
- **Date Selection**: Get current NC time or select custom dates
- **Day Selection**: Choose operational day (1-6)
- **Order Generation**: Create comprehensive orders for all routes
- **Order Confirmation**: Persistent state management with confirmation workflow

### Relay Tab
- **Interactive Display**: Visual trailer cards organized by location
- **Trailer Editing**: Type trailer identifier (e.g., "Greenville_1") to edit
- **Seal & Trailer Numbers**: Input and update trailer identification
- **Dispatch Operations**: Finalize trailers with permanent dispatch status
- **Real-time Updates**: Live color changes and status updates

## 🔧 Technical Architecture

### Data Management
- **JSON-based Persistence**: Orders, routes, and state stored in structured JSON files
- **Product Catalog**: 252 products with stack heights, tray types, and plant origins
- **Route Configuration**: 135 routes across 16 locations with route-specific data

### System Integration
- **Gradio Web Interface**: Modern, responsive web application
- **Python Backend**: Object-oriented design with modular components
- **External APIs**: WorldTimeAPI integration for accurate timezone handling
- **File I/O Operations**: Robust file management with error handling

### Performance Features
- **Efficient Processing**: Optimized algorithms for large-scale order processing
- **Memory Management**: Global state management with persistent storage
- **Error Handling**: Comprehensive error management and user feedback
- **Real-time Updates**: Live interface updates without page refreshes

## 📊 System Capabilities

- **Scale**: Handles 135+ routes across 16+ locations
- **Products**: Manages 252+ products with specific configurations
- **Trailers**: Supports unlimited trailer allocation with intelligent stacking
- **Operations**: Flexible day-based scheduling (Days 1-6)
- **Integration**: Seamless API integration and external system compatibility

## 🎯 Use Cases

- **Logistics Planning**: Automated relay creation for shipping operations
- **Trailer Management**: Real-time tracking and dispatch management
- **Order Processing**: Comprehensive order generation and management
- **Operational Scheduling**: Date and day-based operational planning
- **Status Tracking**: Live monitoring of trailer dispatch status

## 🚀 Getting Started

1. **Access the System**: Launch the Gradio web interface
2. **Load Data**: System automatically loads products.json and routes.json
3. **Create Orders**: Select date/day and generate orders for all routes
4. **Generate Relay**: Create interactive relay display with trailer assignments
5. **Manage Trailers**: Edit seal/trailer numbers and dispatch trailers
6. **Track Status**: Monitor real-time dispatch status with color-coded interface

## 💡 Key Benefits

- **Automation**: Reduces manual relay planning from hours to minutes
- **Accuracy**: Product-specific calculations ensure optimal trailer utilization
- **Visibility**: Real-time status tracking provides complete operational visibility
- **Efficiency**: Streamlined workflow reduces errors and improves productivity
- **Scalability**: Handles large-scale operations with consistent performance