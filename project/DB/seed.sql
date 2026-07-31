INSERT INTO Farms VALUES
(1,'North Farm','Alexandria'),
(2,'South Farm','Beheira');

INSERT INTO Crops VALUES
(1,'Corn','Growing'),
(2,'Wheat','Harvest Ready'),
(3,'Tomatoes','Seedling');

INSERT INTO Fields VALUES
(1,1,1,'Field A','North Farm - Field A',40,'2026-07-28',2),
(2,1,2,'Field B','North Farm - Field B',25,NULL,NULL),
(3,2,3,'Field C','South Farm - Field C',35,NULL,NULL);

INSERT INTO Chemicals VALUES
(1,'Nitrogen Fertilizer','Fertilizer',0,0,500),
(2,'Herbicide X','Herbicide',1,48,150),
(3,'Pesticide B','Pesticide',0,24,300);

INSERT INTO Workers VALUES
(1,'Ahmed Hassan','Farm Manager',0),
(2,'Sara Ali','Certified Agronomist',1),
(3,'Omar Adel','Worker',0);

INSERT INTO Chemical_Applications VALUES
(1,1,2,1,'Pending','2026-07-30'),
(2,2,1,1,'Completed','2026-07-28');

INSERT INTO Approvals VALUES
(1,2,2,'Approved','2026-07-28');

INSERT INTO Safety_Policies VALUES
(
1,
'Restricted Chemicals',
'Restricted chemicals require approval from a certified agronomist before application.'
);

INSERT INTO Inventory VALUES
(1,1,500,'liters'),
(2,2,150,'liters'),
(3,3,300,'liters');